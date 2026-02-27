"""Data coordinator for Vector integration."""

from __future__ import annotations

import asyncio
import logging
import math
import time
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_PASSWORD, STATE_UNKNOWN
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import (
    CONF_EMAIL,
    CONF_HOST,
    CONF_ROBOT_NAME,
    CONF_SERIAL,
    EXCLUDED_ACTIVITY_STATUS_FLAGS,
    MASTER_VOLUME_OPTIONS,
    QUICK_ACTION_INTENTS,
)

_LOGGER = logging.getLogger(__name__)
_DEFAULT_TIMEOUT_SECONDS = 10.0
_MAX_EVENT_READS = 10
_STREAM_READ_TIMEOUT_SECONDS = 120.0
_STREAM_RECONNECT_DELAY_SECONDS = 3.0
_INITIAL_REFRESH_TIMEOUT_SECONDS = 20.0
_INITIAL_REFRESH_RETRY_ATTEMPTS = 5
_INITIAL_REFRESH_RETRY_DELAY_SECONDS = 3.0
_INITIAL_REFRESH_MAX_RETRY_DELAY_SECONDS = 60.0
_CAMERA_STREAM_READ_TIMEOUT_SECONDS = 30.0
_CAMERA_RECONNECT_DELAY_SECONDS = 2.0
_AUTH_BACKOFF_BASE_DELAY_SECONDS = 15.0
_AUTH_BACKOFF_MAX_DELAY_SECONDS = 300.0
_APP_INTENT_RPC_PATH = "/Anki.Vector.external_interface.ExternalInterface/AppIntent"

_STATUS_IS_MOVING = 0x1
_STATUS_IS_CARRYING_BLOCK = 0x2
_STATUS_IS_PICKING_OR_PLACING = 0x4
_STATUS_IS_PATHING = 0x80
_STATUS_CALM_POWER_MODE = 0x400
_STATUS_IS_ON_CHARGER = 0x1000
_STATUS_IS_CHARGING = 0x2000
_EXCLUDED_ACTIVITY_STATUS_MASK = 0
for _flag in EXCLUDED_ACTIVITY_STATUS_FLAGS:
    _EXCLUDED_ACTIVITY_STATUS_MASK |= _flag


class VectorCoordinator(DataUpdateCoordinator[None]):
    """Coordinate Vector data updates."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        """Initialize coordinator."""
        super().__init__(
            hass=hass,
            logger=_LOGGER,
            name=f"vector_{entry.entry_id}",
        )
        self.entry = entry
        self.current_activity: str = STATE_UNKNOWN
        self.battery_percent: int | None = None
        self.battery_volts: float | None = None
        self.battery_level: str = STATE_UNKNOWN
        self.is_charging: bool | None = None
        self.firmware_version: str | None = None
        self.robot_serial: str | None = None
        self.days_alive: int | None = None
        self.reacted_to_trigger_word: int | None = None
        self.utility_features_used: int | None = None
        self.seconds_petted: int | None = None
        self.distance_moved_cm: int | None = None
        self.master_volume: str | None = None
        self.stimulation_value: float | None = None
        self.stimulation_velocity: float | None = None
        self.stimulation_accel: float | None = None
        self.stimulation_value_before_event: float | None = None
        self.stimulation_min_value: float | None = None
        self.stimulation_max_value: float | None = None
        self.stimulation_emotion_events: tuple[str, ...] = ()
        self.camera_frame: bytes | None = None
        self.camera_frame_updated_monotonic: float | None = None
        self._client: Any | None = None
        self._robot_config: Any | None = None
        self._pyddlvector: Any | None = None
        self._messaging: Any | None = None
        self._event_listener_task: asyncio.Task[None] | None = None
        self._camera_stream_task: asyncio.Task[None] | None = None
        self._camera_stream_lock = asyncio.Lock()
        self._camera_frame_event = asyncio.Event()
        self._settings_lock = asyncio.Lock()
        self._auth_backoff_delay_seconds = _AUTH_BACKOFF_BASE_DELAY_SECONDS
        self._auth_backoff_lock = asyncio.Lock()

    async def _async_update_data(self) -> None:
        """Do initial one-shot load at setup."""
        try:
            client, messaging = await self._async_get_client()
            (
                battery_volts,
                battery_level,
                is_charging,
            ) = await self._async_read_battery_state(
                client,
                messaging,
            )
            firmware_version = await self._async_read_firmware_version(
                client, messaging
            )
            lifetime_stats = await self._async_read_lifetime_stats()
            master_volume = await self._async_read_master_volume()
            activity = self.current_activity
        except Exception as err:
            raise UpdateFailed(f"Failed to update Vector activity: {err}") from err

        self.battery_percent = _battery_percentage_from_wirepod_curve(battery_volts)
        self.battery_volts = battery_volts
        self.battery_level = battery_level
        self.is_charging = is_charging
        self.firmware_version = firmware_version
        if lifetime_stats is not None:
            self.days_alive = lifetime_stats.days_alive
            self.reacted_to_trigger_word = lifetime_stats.reacted_to_trigger_word
            self.utility_features_used = lifetime_stats.utility_features_used
            self.seconds_petted = lifetime_stats.seconds_petted
            self.distance_moved_cm = lifetime_stats.distance_moved_cm
        self.master_volume = master_volume
        self.current_activity = activity
        self._auth_backoff_delay_seconds = _AUTH_BACKOFF_BASE_DELAY_SECONDS
        return None

    async def async_validate_connection(self) -> None:
        """Validate robot connectivity/auth for config entry setup."""
        client, messaging = await self._async_get_client()
        await self._async_read_battery_state(client, messaging)

    async def async_start_event_listener(self) -> None:
        """Start persistent push listener from robot event stream."""
        if (
            self._event_listener_task is not None
            and not self._event_listener_task.done()
        ):
            return
        self._event_listener_task = self.hass.async_create_background_task(
            self._async_event_listener_loop(),
            name=f"vector_event_listener_{self.entry.entry_id}",
        )

    async def async_start_runtime(self) -> None:
        """Initialize runtime data and start push listener without blocking HA startup."""
        retry_delay = _INITIAL_REFRESH_RETRY_DELAY_SECONDS
        for attempt in range(1, _INITIAL_REFRESH_RETRY_ATTEMPTS + 1):
            try:
                await asyncio.wait_for(
                    self.async_refresh(),
                    timeout=_INITIAL_REFRESH_TIMEOUT_SECONDS,
                )
            except TimeoutError:
                _LOGGER.warning(
                    "Initial Vector refresh timed out after %.1fs (attempt %s/%s)",
                    _INITIAL_REFRESH_TIMEOUT_SECONDS,
                    attempt,
                    _INITIAL_REFRESH_RETRY_ATTEMPTS,
                )
            except Exception as err:
                if _is_unauthenticated_error(err):
                    await self._async_handle_auth_failure(
                        "initial refresh",
                        err,
                    )
                    continue
                _LOGGER.warning(
                    "Initial Vector refresh failed (attempt %s/%s): %s",
                    attempt,
                    _INITIAL_REFRESH_RETRY_ATTEMPTS,
                    err,
                )
            else:
                if (
                    self.battery_percent is not None
                    and self.firmware_version is not None
                ):
                    break
                _LOGGER.debug(
                    "Initial refresh incomplete (battery/firmware missing), retrying (%s/%s)",
                    attempt,
                    _INITIAL_REFRESH_RETRY_ATTEMPTS,
                )

            if attempt < _INITIAL_REFRESH_RETRY_ATTEMPTS:
                await asyncio.sleep(retry_delay)
                retry_delay = min(
                    retry_delay * 2,
                    _INITIAL_REFRESH_MAX_RETRY_DELAY_SECONDS,
                )

        await self.async_start_event_listener()

    async def async_shutdown(self) -> None:
        """Disconnect active client resources."""
        if self._event_listener_task is not None:
            self._event_listener_task.cancel()
            try:
                await self._event_listener_task
            except asyncio.CancelledError:
                pass
            finally:
                self._event_listener_task = None

        if self._camera_stream_task is not None:
            self._camera_stream_task.cancel()
            try:
                await self._camera_stream_task
            except asyncio.CancelledError:
                pass
            finally:
                self._camera_stream_task = None

        if self._client is None:
            return
        try:
            await self._client.disconnect()
        finally:
            self._client = None

    async def _async_get_client(self) -> tuple[Any, Any]:
        if self._client is not None:
            if self._messaging is None:
                raise ValueError("Messaging module was not initialized")
            return self._client, self._messaging

        pyddlvector, messaging = await self._async_get_modules()

        robot_config = await self._async_get_runtime_robot_config(
            pyddlvector, messaging
        )

        client = pyddlvector.VectorClient(
            robot_config,
            stub_factory=lambda channel: messaging.client.ExternalInterfaceStub(
                channel
            ),
            default_timeout=_DEFAULT_TIMEOUT_SECONDS,
        )
        await client.connect(timeout=_DEFAULT_TIMEOUT_SECONDS)
        self._client = client
        return client, messaging

    async def _async_get_modules(self) -> tuple[Any, Any]:
        if self._pyddlvector is not None and self._messaging is not None:
            return self._pyddlvector, self._messaging

        pyddlvector, messaging = await self.hass.async_add_executor_job(
            _load_pyddlvector_modules
        )
        self._pyddlvector = pyddlvector
        self._messaging = messaging
        return pyddlvector, messaging

    async def _async_read_current_activity(self, client: Any, messaging: Any) -> str:
        stream = client.stub.EventStream(
            messaging.protocol.EventRequest(),
            timeout=_DEFAULT_TIMEOUT_SECONDS,
        )
        try:
            for _ in range(_MAX_EVENT_READS):
                event_response = await asyncio.wait_for(
                    stream.read(),
                    timeout=_DEFAULT_TIMEOUT_SECONDS,
                )
                if event_response is None or not event_response.HasField("event"):
                    continue

                event_type = event_response.event.WhichOneof("event_type")
                if event_type != "robot_state":
                    continue

                return _derive_activity_from_robot_state(
                    event_response.event.robot_state
                )
        finally:
            stream.cancel()

        return STATE_UNKNOWN

    async def _async_event_listener_loop(self) -> None:
        """Keep a persistent event stream open and push updates to entities."""
        while True:
            stream = None
            try:
                client, messaging = await self._async_get_client()
                stream = client.stub.EventStream(
                    messaging.protocol.EventRequest(),
                )

                while True:
                    try:
                        event_response = await asyncio.wait_for(
                            stream.read(),
                            timeout=_STREAM_READ_TIMEOUT_SECONDS,
                        )
                    except TimeoutError:
                        # No robot_state event within the window; keep listening.
                        continue
                    if event_response is None or not event_response.HasField("event"):
                        continue

                    event_type = event_response.event.WhichOneof("event_type")

                    has_changes = False
                    if event_type == "robot_state":
                        robot_state = event_response.event.robot_state
                        next_activity = _derive_activity_from_robot_state(robot_state)
                        next_charging = _charging_from_robot_state(robot_state)

                        if next_activity != self.current_activity:
                            self.current_activity = next_activity
                            has_changes = True
                        if next_charging != self.is_charging:
                            self.is_charging = next_charging
                            has_changes = True
                    elif event_type == "stimulation_info":
                        has_changes = self._update_stimulation_from_event(
                            event_response.event.stimulation_info
                        )
                    else:
                        continue

                    if has_changes:
                        self.async_set_updated_data(None)
            except asyncio.CancelledError:
                raise
            except Exception as err:
                if _is_unauthenticated_error(err):
                    await self._async_handle_auth_failure("event stream", err)
                    continue
                _LOGGER.warning(
                    "Vector event stream interrupted: %s",
                    err,
                )
                await asyncio.sleep(_STREAM_RECONNECT_DELAY_SECONDS)
            finally:
                if stream is not None:
                    stream.cancel()

    async def _async_read_battery_state(
        self, client: Any, messaging: Any
    ) -> tuple[float, str, bool]:
        response = await client.rpc(
            "BatteryState",
            messaging.protocol.BatteryStateRequest(),
            timeout=_DEFAULT_TIMEOUT_SECONDS,
        )

        level_value = int(getattr(response, "battery_level", 0))
        level_name = _normalize_battery_level_name(
            _enum_name(messaging.protocol.BatteryLevel, level_value),
        )
        battery_volts = float(getattr(response, "battery_volts", 0.0))
        is_charging = bool(getattr(response, "is_charging", False))
        return battery_volts, level_name, is_charging

    async def _async_read_firmware_version(
        self, client: Any, messaging: Any
    ) -> str | None:
        response = await client.rpc(
            "VersionState",
            messaging.protocol.VersionStateRequest(),
            timeout=_DEFAULT_TIMEOUT_SECONDS,
        )
        os_version = str(getattr(response, "os_version", "")).strip()
        engine_build_id = str(getattr(response, "engine_build_id", "")).strip()
        return os_version or engine_build_id or None

    async def _async_read_lifetime_stats(self) -> Any | None:
        if self._pyddlvector is None or self._client is None:
            return None

        try:
            return await self._pyddlvector.fetch_lifetime_statistics(
                self._client,
                timeout=_DEFAULT_TIMEOUT_SECONDS,
            )
        except Exception as err:
            _LOGGER.debug("Failed to read lifetime stats: %s", err)
            return None

    async def _async_read_master_volume(self) -> str | None:
        if self._pyddlvector is None or self._client is None:
            return None

        try:
            value = await self._pyddlvector.fetch_master_volume(
                self._client,
                timeout=_DEFAULT_TIMEOUT_SECONDS,
            )
        except Exception as err:
            _LOGGER.debug("Failed to read master volume: %s", err)
            return None

        normalized = str(value).strip().lower()
        if normalized not in MASTER_VOLUME_OPTIONS:
            _LOGGER.debug(
                "Ignoring unsupported master volume value from robot: %s", value
            )
            return None
        return normalized

    async def async_set_master_volume(self, value: str) -> None:
        """Update robot master volume and push state update."""
        normalized = value.strip().lower()
        if normalized not in MASTER_VOLUME_OPTIONS:
            raise ValueError(f"Unsupported master volume option: {value}")

        async with self._settings_lock:
            client, _ = await self._async_get_client()
            pyddlvector, _ = await self._async_get_modules()
            selected = await pyddlvector.update_master_volume(
                client,
                normalized,
                timeout=_DEFAULT_TIMEOUT_SECONDS,
            )
            self.master_volume = str(selected).strip().lower()
            self.async_set_updated_data(None)

    async def async_say_text(
        self,
        *,
        text: str,
        use_vector_voice: bool = True,
        duration_scalar: float = 1.0,
        pitch_scalar: float = 0.0,
    ) -> None:
        """Speak text using the robot TTS engine."""
        normalized_text = text.strip()
        if not normalized_text:
            raise ValueError("Text must not be empty")

        if not (0.05 <= duration_scalar <= 20.0):
            raise ValueError("duration_scalar must be between 0.05 and 20.0")
        if not (-1.0 <= pitch_scalar <= 1.0):
            raise ValueError("pitch_scalar must be between -1.0 and 1.0")

        client, messaging = await self._async_get_client()
        request_variants: list[Any] = []
        primary_kwargs: dict[str, Any] = {
            "text": normalized_text,
            "use_vector_voice": bool(use_vector_voice),
            "duration_scalar": float(duration_scalar),
        }
        if pitch_scalar != 0.0:
            primary_kwargs["pitch_scalar"] = float(pitch_scalar)
        request_variants.append(messaging.protocol.SayTextRequest(**primary_kwargs))

        if use_vector_voice:
            request_variants.append(
                messaging.protocol.SayTextRequest(
                    text=normalized_text,
                    use_vector_voice=False,
                    duration_scalar=float(duration_scalar),
                )
            )

        request_variants.append(messaging.protocol.SayTextRequest(text=normalized_text))

        last_error: Exception | None = None
        for request in request_variants:
            try:
                await client.rpc(
                    "SayText",
                    request,
                    timeout=_DEFAULT_TIMEOUT_SECONDS,
                )
                return
            except Exception as err:
                last_error = err
                details = str(err).lower()
                if "failed to say text" not in details:
                    raise

                # Some firmware variants require explicit behavior control
                # before direct SayText calls.
                granted = await self._async_assume_behavior_control(client, messaging)
                if granted:
                    try:
                        await client.rpc(
                            "SayText",
                            request,
                            timeout=_DEFAULT_TIMEOUT_SECONDS,
                        )
                        return
                    except Exception as retry_err:
                        last_error = retry_err
                        retry_details = str(retry_err).lower()
                        if "failed to say text" not in retry_details:
                            raise

        if last_error is not None:
            raise last_error

    async def _async_assume_behavior_control(self, client: Any, messaging: Any) -> bool:
        """Try to acquire temporary behavior control for one action."""
        stream = None
        try:
            stream = client.stub.AssumeBehaviorControl(
                messaging.protocol.BehaviorControlRequest(
                    control_request=messaging.protocol.ControlRequest(
                        priority=messaging.protocol.ControlRequest.DEFAULT,
                    )
                ),
                timeout=_DEFAULT_TIMEOUT_SECONDS,
            )
            response = await asyncio.wait_for(
                stream.read(),
                timeout=_DEFAULT_TIMEOUT_SECONDS,
            )
            if response is None:
                return False

            return response.WhichOneof("response_type") == "control_granted_response"
        except Exception as err:
            _LOGGER.debug("Failed to assume behavior control for SayText retry: %s", err)
            return False
        finally:
            if stream is not None:
                stream.cancel()

    async def async_trigger_quick_action(self, action_key: str) -> None:
        """Trigger one supported quick action intent."""
        intent = QUICK_ACTION_INTENTS.get(action_key)
        if intent is None:
            raise ValueError(f"Unsupported quick action: {action_key}")

        client, messaging = await self._async_get_client()
        request = messaging.protocol.AppIntentRequest(intent=intent)
        if hasattr(client.stub, "AppIntent"):
            await client.rpc(
                "AppIntent",
                request,
                timeout=_DEFAULT_TIMEOUT_SECONDS,
            )
            return

        await client.unary_unary(
            _APP_INTENT_RPC_PATH,
            request,
            request_serializer=messaging.protocol.AppIntentRequest.SerializeToString,
            response_deserializer=messaging.protocol.AppIntentResponse.FromString,
            timeout=_DEFAULT_TIMEOUT_SECONDS,
        )

    async def async_start_camera_stream(self) -> None:
        """Ensure persistent camera stream task is running."""
        async with self._camera_stream_lock:
            if (
                self._camera_stream_task is not None
                and not self._camera_stream_task.done()
            ):
                return
            self._camera_stream_task = self.hass.async_create_background_task(
                self._async_camera_stream_loop(),
                name=f"vector_camera_stream_{self.entry.entry_id}",
            )

    async def async_get_latest_camera_frame(
        self,
        *,
        wait_timeout: float = 1.0,
    ) -> bytes | None:
        """Return latest JPEG frame, optionally waiting for first frame."""
        await self.async_start_camera_stream()

        if self.camera_frame is not None:
            return self.camera_frame

        try:
            await asyncio.wait_for(
                self._camera_frame_event.wait(), timeout=wait_timeout
            )
        except TimeoutError:
            return None

        return self.camera_frame

    async def _async_camera_stream_loop(self) -> None:
        """Keep persistent camera feed stream and cache latest frame."""
        while True:
            stream = None
            try:
                client, messaging = await self._async_get_client()
                stream = client.stub.CameraFeed(messaging.protocol.CameraFeedRequest())

                while True:
                    response = await asyncio.wait_for(
                        stream.read(),
                        timeout=_CAMERA_STREAM_READ_TIMEOUT_SECONDS,
                    )
                    if response is None:
                        continue

                    frame = _extract_camera_frame_bytes(self._pyddlvector, response)
                    if frame is None:
                        continue

                    # Keep only newest frame to prevent queue/latency buildup.
                    self.camera_frame = frame
                    self.camera_frame_updated_monotonic = time.monotonic()
                    self._camera_frame_event.set()
            except asyncio.CancelledError:
                raise
            except Exception as err:
                if _is_unauthenticated_error(err):
                    await self._async_handle_auth_failure("camera stream", err)
                    continue
                await asyncio.sleep(_CAMERA_RECONNECT_DELAY_SECONDS)
            finally:
                if stream is not None:
                    stream.cancel()

    def _update_stimulation_from_event(self, stimulation_info: Any) -> bool:
        pyddlvector = self._pyddlvector
        if pyddlvector is not None and hasattr(pyddlvector, "parse_stimulation_info"):
            parsed = pyddlvector.parse_stimulation_info(stimulation_info)
            next_snapshot = (
                float(parsed.value),
                float(parsed.velocity),
                float(parsed.accel),
                float(parsed.value_before_event),
                float(parsed.min_value),
                float(parsed.max_value),
                tuple(str(event) for event in parsed.emotion_events),
            )
        else:
            next_snapshot = _normalize_stimulation_snapshot(stimulation_info)

        current_snapshot = (
            self.stimulation_value,
            self.stimulation_velocity,
            self.stimulation_accel,
            self.stimulation_value_before_event,
            self.stimulation_min_value,
            self.stimulation_max_value,
            self.stimulation_emotion_events,
        )
        if current_snapshot == next_snapshot:
            return False

        (
            self.stimulation_value,
            self.stimulation_velocity,
            self.stimulation_accel,
            self.stimulation_value_before_event,
            self.stimulation_min_value,
            self.stimulation_max_value,
            self.stimulation_emotion_events,
        ) = next_snapshot
        return True

    async def _async_handle_auth_failure(self, source: str, err: Exception) -> None:
        async with self._auth_backoff_lock:
            delay = self._auth_backoff_delay_seconds
            self._auth_backoff_delay_seconds = min(
                self._auth_backoff_delay_seconds * 2,
                _AUTH_BACKOFF_MAX_DELAY_SECONDS,
            )

        _LOGGER.warning(
            "Vector %s authentication failed; backing off for %.0fs: %s",
            source,
            delay,
            err,
        )
        await self._async_reset_client(clear_robot_config=True)
        await asyncio.sleep(delay)

    async def _async_reset_client(self, *, clear_robot_config: bool) -> None:
        client = self._client
        self._client = None
        if clear_robot_config:
            self._robot_config = None

        if client is not None:
            try:
                await client.disconnect()
            except Exception:
                _LOGGER.debug(
                    "Vector client disconnect during reset failed", exc_info=True
                )

    async def _async_get_runtime_robot_config(
        self, pyddlvector: Any, messaging: Any
    ) -> Any:
        if self._robot_config is not None:
            return self._robot_config

        entry_data = self.entry.data

        host = (entry_data.get(CONF_HOST) or "").strip()
        robot_name = (entry_data.get(CONF_ROBOT_NAME) or "").strip()
        serial = (entry_data.get(CONF_SERIAL) or "").strip() or None
        email = (entry_data.get(CONF_EMAIL) or "").strip() or None
        password = (entry_data.get(CONF_PASSWORD) or "").strip() or None

        if not host or not robot_name:
            raise ValueError("Missing required robot identity values in config entry")
        mode = _resolve_provision_mode(serial=serial, email=email, password=password)
        robot_config = await pyddlvector.provision_runtime_robot(
            mode=mode,
            name=robot_name,
            ip=host,
            serial=serial,
            username=email,
            password=password,
            stub_factory=lambda channel: messaging.client.ExternalInterfaceStub(
                channel
            ),
            request_factory=_auth_request_factory(messaging),
            timeout=_DEFAULT_TIMEOUT_SECONDS,
        )
        serial_value = getattr(robot_config, "serial", None)
        if isinstance(serial_value, str):
            normalized = serial_value.strip().lower()
            self.robot_serial = normalized or None
        else:
            self.robot_serial = None
        self._robot_config = robot_config
        return robot_config

    def set_current_activity(self, activity: str | None) -> None:
        """Set current activity and notify entities."""
        normalized = (activity or "").strip().lower()
        self.current_activity = normalized or STATE_UNKNOWN
        self.async_set_updated_data(None)


def _derive_activity_from_robot_state(robot_state: Any) -> str:
    """Derive normalized activity string from robot state payload."""
    status = int(getattr(robot_state, "status", 0))
    status &= ~_EXCLUDED_ACTIVITY_STATUS_MASK

    if status & _STATUS_CALM_POWER_MODE:
        return "sleeping"

    left_speed = abs(float(getattr(robot_state, "left_wheel_speed_mmps", 0.0)))
    right_speed = abs(float(getattr(robot_state, "right_wheel_speed_mmps", 0.0)))
    if left_speed + right_speed > 1.0:
        return "moving"

    if status & (
        _STATUS_IS_MOVING | _STATUS_IS_PICKING_OR_PLACING | _STATUS_IS_PATHING
    ):
        return "moving"

    touch_data = getattr(robot_state, "touch_data", None)
    if bool(getattr(touch_data, "is_being_touched", False)):
        return "being_touched"

    carrying_object_id = int(getattr(robot_state, "carrying_object_id", -1))
    if status & _STATUS_IS_CARRYING_BLOCK or carrying_object_id >= 0:
        return "carrying_object"

    if status & _STATUS_IS_CHARGING:
        return "charging"

    if status & _STATUS_IS_ON_CHARGER:
        return "on_charger"

    return "idle"


def _charging_from_robot_state(robot_state: Any) -> bool:
    status = int(getattr(robot_state, "status", 0))
    return bool(status & _STATUS_IS_CHARGING)


def _enum_name(enum_cls: Any, value: int) -> str:
    try:
        return str(enum_cls.Name(value))
    except ValueError:
        return f"UNKNOWN_{value}"


def _normalize_battery_level_name(level_name: str) -> str:
    normalized = level_name.strip().upper()
    prefix = "BATTERY_LEVEL_"
    if normalized.startswith(prefix):
        normalized = normalized[len(prefix) :]
    return normalized.lower() or STATE_UNKNOWN


def _auth_request_factory(messaging: Any):
    def _build(session_id: str, client_name: str) -> Any:
        return messaging.protocol.UserAuthenticationRequest(
            user_session_id=session_id.encode("utf-8"),
            client_name=client_name.encode("utf-8"),
        )

    return _build


def _load_pyddlvector_modules() -> tuple[Any, Any]:
    """Load pyddlvector + protobuf messaging modules outside the event loop."""
    try:
        import pyddlvector
    except ImportError as err:
        raise ValueError("pyddlvector dependency is not installed") from err

    return pyddlvector, pyddlvector.messaging


def _battery_percentage_from_wirepod_curve(voltage: float) -> int:
    """Mirror wire-pod battery.js percentage conversion from battery volts."""
    max_voltage = 4.1
    mid_voltage = 3.85
    min_voltage = 3.5

    if voltage >= max_voltage:
        percentage = 100.0
    elif voltage >= mid_voltage:
        scaled_voltage = (voltage - mid_voltage) / (max_voltage - mid_voltage)
        percentage = 80 + 20 * math.log10(1 + scaled_voltage * 9)
    elif voltage >= min_voltage:
        scaled_voltage = (voltage - min_voltage) / (mid_voltage - min_voltage)
        percentage = 80 * math.log10(1 + scaled_voltage * 9)
    elif not voltage:
        percentage = 70.0
    else:
        percentage = 0.0

    bounded = max(0, min(100, round(percentage)))
    return int(bounded)


def _normalize_stimulation_snapshot(
    stimulation_info: Any,
) -> tuple[float, float, float, float, float, float, tuple[str, ...]]:
    emotion_events_raw = getattr(stimulation_info, "emotion_events", ())
    emotion_events = tuple(
        event.strip()
        for event in emotion_events_raw
        if isinstance(event, str) and event.strip()
    )

    return (
        float(getattr(stimulation_info, "value", 0.0)),
        float(getattr(stimulation_info, "velocity", 0.0)),
        float(getattr(stimulation_info, "accel", 0.0)),
        float(getattr(stimulation_info, "value_before_event", 0.0)),
        float(getattr(stimulation_info, "min_value", 0.0)),
        float(getattr(stimulation_info, "max_value", 0.0)),
        emotion_events,
    )


def _extract_camera_frame_bytes(pyddlvector: Any | None, response: Any) -> bytes | None:
    if pyddlvector is not None and hasattr(pyddlvector, "extract_camera_frame"):
        parsed = pyddlvector.extract_camera_frame(response)
        if parsed is not None:
            return bytes(getattr(parsed, "data", b""))

    image_encoding = int(getattr(response, "image_encoding", -1))
    if image_encoding not in {6, 7, 8, 9, 10}:
        return None
    data = bytes(getattr(response, "data", b""))
    return data or None


def _is_unauthenticated_error(err: Exception) -> bool:
    status_code = getattr(err, "status_code", None)
    if status_code is not None and str(status_code).endswith("UNAUTHENTICATED"):
        return True

    details = str(err).upper()
    return "UNAUTHENTICATED" in details or "STATUS: 401" in details


def _resolve_provision_mode(
    *,
    serial: str | None,
    email: str | None,
    password: str | None,
) -> str:
    if not serial:
        raise ValueError("Serial is required")

    has_email = bool(email)
    has_password = bool(password)

    if has_email or has_password:
        if not (has_email and has_password):
            raise ValueError("Official mode requires both email and password")
        return "official"

    return "wirepod"
