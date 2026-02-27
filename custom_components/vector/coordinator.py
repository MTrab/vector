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
_SAY_TEXT_WAKE_WAIT_TIMEOUT_SECONDS = 120.0
_SAY_TEXT_WAKE_POLL_INTERVAL_SECONDS = 2.0

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
        self.orientation_roll_rad: float | None = None
        self.orientation_pitch_rad: float | None = None
        self.orientation_yaw_rad: float | None = None
        self.lift_height_mm: float | None = None
        self.camera_frame: bytes | None = None
        self.camera_frame_updated_monotonic: float | None = None
        self._client: Any | None = None
        self._robot_config: Any | None = None
        self._pyddlvector: Any | None = None
        self._messaging: Any | None = None
        self._activity_tracker: Any | None = None
        self._telemetry_filter: Any | None = None
        self._event_listener_task: asyncio.Task[None] | None = None
        self._camera_stream_task: asyncio.Task[None] | None = None
        self._wake_enable_stream_task: asyncio.Task[None] | None = None
        self._wake_camera_restart_task: asyncio.Task[None] | None = None
        self._camera_stream_lock = asyncio.Lock()
        self._image_stream_enable_lock = asyncio.Lock()
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
        self.firmware_version = await self._async_read_firmware_version(
            client, messaging
        )

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

        if self._wake_enable_stream_task is not None:
            self._wake_enable_stream_task.cancel()
            try:
                await self._wake_enable_stream_task
            except asyncio.CancelledError:
                pass
            finally:
                self._wake_enable_stream_task = None

        if self._wake_camera_restart_task is not None:
            self._wake_camera_restart_task.cancel()
            try:
                await self._wake_camera_restart_task
            except asyncio.CancelledError:
                pass
            finally:
                self._wake_camera_restart_task = None

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
        if self._activity_tracker is None and hasattr(
            pyddlvector, "RobotActivityTracker"
        ):
            self._activity_tracker = pyddlvector.RobotActivityTracker()
        if self._telemetry_filter is None and hasattr(pyddlvector, "TelemetryFilter"):
            self._telemetry_filter = pyddlvector.TelemetryFilter()
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
                event = event_response.event
                if self._activity_tracker is not None:
                    self._activity_tracker.observe_event(event)

                event_type = event.WhichOneof("event_type")
                if event_type != "robot_state":
                    continue

                if self._activity_tracker is not None:
                    activity = self._activity_tracker.activity_from_robot_state(
                        event.robot_state
                    )
                    return _normalize_activity_state(activity)

                return _derive_activity_from_robot_state(event.robot_state)
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

                    event = event_response.event
                    if self._activity_tracker is not None:
                        self._activity_tracker.observe_event(event)
                    event_type = event.WhichOneof("event_type")

                    has_changes = False
                    if event_type == "robot_state":
                        robot_state = event.robot_state
                        previous_activity = self.current_activity
                        if self._activity_tracker is not None:
                            next_activity = _normalize_activity_state(
                                self._activity_tracker.activity_from_robot_state(
                                    robot_state
                                )
                            )
                        else:
                            next_activity = _derive_activity_from_robot_state(
                                robot_state
                            )
                        next_charging = _charging_from_robot_state(robot_state)
                        (
                            next_roll,
                            next_pitch,
                            next_yaw,
                            next_lift_height,
                        ) = _extract_robot_telemetry_snapshot(
                            self._pyddlvector,
                            self._telemetry_filter,
                            robot_state,
                        )

                        if next_activity != self.current_activity:
                            self.current_activity = next_activity
                            has_changes = True
                            if (
                                previous_activity == "sleeping"
                                and next_activity != "sleeping"
                            ):
                                self._async_schedule_enable_image_streaming_on_wake()
                                self._async_schedule_camera_stream_restart_on_wake()
                        if next_charging != self.is_charging:
                            self.is_charging = next_charging
                            has_changes = True
                        if next_roll is not None and next_roll != self.orientation_roll_rad:
                            self.orientation_roll_rad = next_roll
                            has_changes = True
                        if next_pitch is not None and next_pitch != self.orientation_pitch_rad:
                            self.orientation_pitch_rad = next_pitch
                            has_changes = True
                        if next_yaw is not None and next_yaw != self.orientation_yaw_rad:
                            self.orientation_yaw_rad = next_yaw
                            has_changes = True
                        if (
                            next_lift_height is not None
                            and next_lift_height != self.lift_height_mm
                        ):
                            self.lift_height_mm = next_lift_height
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
        request_kwargs: dict[str, Any] = {
            "text": normalized_text,
            "use_vector_voice": bool(use_vector_voice),
            "duration_scalar": float(duration_scalar),
        }
        if pitch_scalar != 0.0:
            request_kwargs["pitch_scalar"] = float(pitch_scalar)
        request = messaging.protocol.SayTextRequest(**request_kwargs)

        if hasattr(client.stub, "BehaviorControl"):
            try:
                await self._async_say_text_with_behavior_control(
                    client,
                    messaging,
                    request,
                    priority=messaging.protocol.ControlRequest.DEFAULT,
                )
            except ValueError as err:
                if (
                    "did not grant behavior control" not in str(err).lower()
                    or not await self._async_wait_until_awake_for_say_text(
                        timeout=_SAY_TEXT_WAKE_WAIT_TIMEOUT_SECONDS
                    )
                ):
                    raise
                await self._async_say_text_with_behavior_control(
                    client,
                    messaging,
                    request,
                    priority=messaging.protocol.ControlRequest.DEFAULT,
                )
            return

        await client.rpc("SayText", request, timeout=_DEFAULT_TIMEOUT_SECONDS)

    async def _async_wait_until_awake_for_say_text(self, *, timeout: float) -> bool:
        """Wait until robot is no longer in sleeping activity state."""
        elapsed = 0.0
        while elapsed < timeout:
            if self.current_activity != "sleeping":
                return True
            await asyncio.sleep(_SAY_TEXT_WAKE_POLL_INTERVAL_SECONDS)
            elapsed += _SAY_TEXT_WAKE_POLL_INTERVAL_SECONDS
        return self.current_activity != "sleeping"

    async def _async_say_text_with_behavior_control(
        self,
        client: Any,
        messaging: Any,
        say_text_request: Any,
        *,
        priority: int,
    ) -> None:
        """Run one SayText call while holding a live behavior-control stream."""
        if not hasattr(client.stub, "BehaviorControl"):
            raise ValueError("BehaviorControl not supported by robot stub")

        stream = None
        granted = False
        try:
            stream = client.stub.BehaviorControl(
                timeout=_DEFAULT_TIMEOUT_SECONDS,
            )
            await stream.write(
                messaging.protocol.BehaviorControlRequest(
                    control_request=messaging.protocol.ControlRequest(
                        priority=priority,
                    )
                )
            )

            for _ in range(5):
                response = await asyncio.wait_for(
                    stream.read(),
                    timeout=_DEFAULT_TIMEOUT_SECONDS,
                )
                if response is None:
                    continue

                response_type = response.WhichOneof("response_type")
                if response_type == "control_granted_response":
                    granted = True
                    break
                if response_type in {
                    "control_lost_event",
                    "reserved_control_lost_event",
                }:
                    break

            if not granted:
                raise ValueError("Vector did not grant behavior control for SayText")

            await client.rpc(
                "SayText",
                say_text_request,
                timeout=_DEFAULT_TIMEOUT_SECONDS,
            )
        finally:
            if stream is not None:
                try:
                    await stream.write(
                        messaging.protocol.BehaviorControlRequest(
                            control_release=messaging.protocol.ControlRelease(),
                        )
                    )
                except Exception:
                    _LOGGER.debug(
                        "Failed sending behavior control release after SayText",
                        exc_info=True,
                    )

                try:
                    await stream.done_writing()
                except Exception:
                    pass

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
                await self._async_enable_image_streaming(client, messaging)
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
                if isinstance(err, TimeoutError):
                    _LOGGER.debug(
                        "Vector camera stream timed out waiting for frames; reconnecting"
                    )
                    await asyncio.sleep(_CAMERA_RECONNECT_DELAY_SECONDS)
                    continue
                details = str(err).strip()
                if details:
                    _LOGGER.debug("Vector camera stream interrupted: %s", details)
                else:
                    _LOGGER.debug(
                        "Vector camera stream interrupted (%s)",
                        err.__class__.__name__,
                        exc_info=True,
                    )
                await asyncio.sleep(_CAMERA_RECONNECT_DELAY_SECONDS)
            finally:
                if stream is not None:
                    stream.cancel()

    async def _async_enable_image_streaming(self, client: Any, messaging: Any) -> None:
        """Enable image streaming when supported by the robot stub."""
        if self.current_activity == "sleeping":
            return

        if not hasattr(client.stub, "EnableImageStreaming"):
            return

        request_cls = getattr(messaging.protocol, "EnableImageStreamingRequest", None)
        if request_cls is None:
            return

        async with self._image_stream_enable_lock:
            if self.current_activity == "sleeping":
                return

            request_kwargs: dict[str, Any] = {"enable": True}
            descriptor = getattr(request_cls, "DESCRIPTOR", None)
            fields_by_name = getattr(descriptor, "fields_by_name", {})
            if "enable_high_resolution" in fields_by_name:
                request_kwargs["enable_high_resolution"] = False

            try:
                request = request_cls(**request_kwargs)
                await client.rpc(
                    "EnableImageStreaming",
                    request,
                    timeout=_DEFAULT_TIMEOUT_SECONDS,
                )
            except Exception as err:
                _LOGGER.debug("Failed to enable image streaming: %s", err)

    def _async_schedule_enable_image_streaming_on_wake(self) -> None:
        """Schedule one image-stream enable attempt after wake transitions."""
        if (
            self._wake_enable_stream_task is not None
            and not self._wake_enable_stream_task.done()
        ):
            return
        self._wake_enable_stream_task = self.hass.async_create_background_task(
            self._async_enable_image_streaming_on_wake(),
            name=f"vector_wake_enable_stream_{self.entry.entry_id}",
        )

    def _async_schedule_camera_stream_restart_on_wake(self) -> None:
        """Schedule one camera-stream restart attempt after wake transitions."""
        if (
            self._wake_camera_restart_task is not None
            and not self._wake_camera_restart_task.done()
        ):
            return
        self._wake_camera_restart_task = self.hass.async_create_background_task(
            self._async_restart_camera_stream_on_wake(),
            name=f"vector_wake_restart_camera_stream_{self.entry.entry_id}",
        )

    async def _async_enable_image_streaming_on_wake(self) -> None:
        """Try enabling image streaming once after waking up."""
        try:
            client, messaging = await self._async_get_client()
            await self._async_enable_image_streaming(client, messaging)
        except asyncio.CancelledError:
            raise
        except Exception as err:
            _LOGGER.debug("Failed scheduling wake image stream enable: %s", err)
        finally:
            self._wake_enable_stream_task = None

    async def _async_restart_camera_stream_on_wake(self) -> None:
        """Restart running camera stream task to reduce wake-to-frame latency."""
        try:
            task = self._camera_stream_task
            if task is None or task.done():
                return

            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
            finally:
                self._camera_stream_task = None

            await self.async_start_camera_stream()
        except asyncio.CancelledError:
            raise
        except Exception as err:
            _LOGGER.debug("Failed restarting camera stream on wake: %s", err)
        finally:
            self._wake_camera_restart_task = None

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
        if self._telemetry_filter is not None and hasattr(
            self._telemetry_filter, "reset"
        ):
            self._telemetry_filter.reset()

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
        self.current_activity = _normalize_activity_state(activity)
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


def _normalize_activity_state(activity: str | None) -> str:
    normalized = (activity or "").strip().lower().replace("-", "_")
    if not normalized:
        return STATE_UNKNOWN

    aliases: dict[str, str] = {
        "falling": "falling",
        "cliff detected": "cliff_detected",
        "being held": "being_held",
        "picked up": "picked_up",
        "exploring from charger": "exploring_from_charger",
        "looking for faces": "looking_for_faces",
        "looking for charger": "looking_for_charger",
        "looking for cubes": "looking_for_cubes",
        "looking for objects": "looking_for_objects",
        "picking or placing object": "picking_or_placing_object",
        "carrying an object": "carrying_object",
        "exploring": "exploring",
        "button pressed": "button_pressed",
        "idle / standing still": "idle",
        "ready": "ready",
        "standing still while carrying an object": "carrying_object",
        "being touched": "being_touched",
        "on charger": "on_charger",
    }
    return aliases.get(normalized, normalized)


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


def _extract_robot_telemetry_snapshot(
    pyddlvector: Any | None,
    telemetry_filter: Any | None,
    robot_state: Any,
) -> tuple[float | None, float | None, float | None, float | None]:
    if pyddlvector is not None and hasattr(pyddlvector, "extract_robot_telemetry"):
        telemetry = pyddlvector.extract_robot_telemetry(robot_state)
        if telemetry_filter is not None and hasattr(telemetry_filter, "process"):
            telemetry = telemetry_filter.process(telemetry)
            if telemetry is None:
                return (None, None, None, None)
        return (
            float(getattr(telemetry, "roll_rad", 0.0)),
            float(getattr(telemetry, "pitch_rad", 0.0)),
            float(getattr(telemetry, "yaw_rad", 0.0)),
            float(getattr(telemetry, "lift_height_mm", 0.0)),
        )

    pitch_rad = getattr(robot_state, "pose_pitch_rad", None)
    yaw_rad = getattr(robot_state, "pose_angle_rad", None)
    lift_height_mm = getattr(robot_state, "lift_height_mm", None)
    return (
        None,
        float(pitch_rad) if pitch_rad is not None else None,
        float(yaw_rad) if yaw_rad is not None else None,
        float(lift_height_mm) if lift_height_mm is not None else None,
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
