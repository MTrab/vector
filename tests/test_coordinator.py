"""Tests for Vector coordinator behavior."""

from __future__ import annotations

from types import SimpleNamespace

from custom_components.vector.coordinator import (
    VectorCoordinator,
    _battery_percentage_from_wirepod_curve,
    _derive_activity_from_robot_state,
    _extract_robot_telemetry_snapshot,
    _extract_camera_frame_bytes,
    _is_unauthenticated_error,
    _normalize_activity_state,
    _normalize_battery_level_name,
    _normalize_stimulation_snapshot,
    _resolve_provision_mode,
)


def _state(**kwargs):
    defaults = {
        "status": 0,
        "left_wheel_speed_mmps": 0.0,
        "right_wheel_speed_mmps": 0.0,
        "touch_data": SimpleNamespace(is_being_touched=False),
        "carrying_object_id": -1,
    }
    defaults.update(kwargs)
    return SimpleNamespace(**defaults)


def test_derive_activity_sleeping_from_calm_power_mode() -> None:
    """Robot in calm power mode should map to sleeping."""
    robot_state = _state(status=0x400)

    assert _derive_activity_from_robot_state(robot_state) == "sleeping"


def test_derive_activity_moving_from_wheel_speed() -> None:
    """Wheel speed should map to moving."""
    robot_state = _state(left_wheel_speed_mmps=24.0, right_wheel_speed_mmps=18.0)

    assert _derive_activity_from_robot_state(robot_state) == "moving"


def test_derive_activity_charging() -> None:
    """Charging bit should map to charging."""
    robot_state = _state(status=0x2000)

    assert _derive_activity_from_robot_state(robot_state) == "charging"


def test_normalize_activity_state_new_labels() -> None:
    """New pyddlvector activity labels should map to sensor state keys."""
    assert _normalize_activity_state("Falling") == "falling"
    assert _normalize_activity_state("Cliff detected") == "cliff_detected"
    assert _normalize_activity_state("Being held") == "being_held"
    assert _normalize_activity_state("Picked up") == "picked_up"
    assert _normalize_activity_state("Exploring from charger") == "exploring_from_charger"
    assert _normalize_activity_state("Looking for faces") == "looking_for_faces"
    assert _normalize_activity_state("Looking for charger") == "looking_for_charger"
    assert _normalize_activity_state("Picking or placing object") == "picking_or_placing_object"
    assert _normalize_activity_state("Carrying an object") == "carrying_object"
    assert _normalize_activity_state("Button pressed") == "button_pressed"
    assert _normalize_activity_state("Ready") == "ready"
    assert _normalize_activity_state("Idle / standing still") == "idle"


def test_normalize_battery_level_name() -> None:
    """Battery enum names should normalize to simple lowercase values."""
    assert _normalize_battery_level_name("BATTERY_LEVEL_NOMINAL") == "nominal"


def test_battery_percentage_from_wirepod_curve() -> None:
    """Battery percentage should follow wire-pod voltage curve."""
    assert _battery_percentage_from_wirepod_curve(4.10) == 100
    assert _battery_percentage_from_wirepod_curve(3.85) == 80
    assert _battery_percentage_from_wirepod_curve(3.50) == 0
    assert _battery_percentage_from_wirepod_curve(0.0) == 70


def test_normalize_stimulation_snapshot() -> None:
    """Stimulation payload should normalize into immutable snapshot tuple."""
    payload = SimpleNamespace(
        value=0.42,
        velocity=0.11,
        accel=-0.03,
        value_before_event=0.39,
        min_value=0.0,
        max_value=1.0,
        emotion_events=[" Frustrated ", "", "Excited"],
    )

    snapshot = _normalize_stimulation_snapshot(payload)

    assert snapshot == (0.42, 0.11, -0.03, 0.39, 0.0, 1.0, ("Frustrated", "Excited"))


def test_extract_camera_frame_bytes_fallback_jpeg() -> None:
    """JPEG encodings should be extracted even without module helper."""
    response = SimpleNamespace(image_encoding=7, data=b"\xff\xd8\xff")
    assert _extract_camera_frame_bytes(None, response) == b"\xff\xd8\xff"


def test_extract_robot_telemetry_snapshot_from_pyddlvector_helper() -> None:
    """Telemetry helper should use pyddlvector extract_robot_telemetry when available."""
    telemetry = SimpleNamespace(
        roll_rad=0.11,
        pitch_rad=-0.22,
        yaw_rad=1.57,
        lift_height_mm=33.3,
    )
    pyddlvector = SimpleNamespace(extract_robot_telemetry=lambda _state: telemetry)

    assert _extract_robot_telemetry_snapshot(pyddlvector, None, object()) == (
        0.11,
        -0.22,
        1.57,
        33.3,
    )


def test_extract_robot_telemetry_snapshot_fallback_without_helper() -> None:
    """Fallback should still expose pitch/yaw/lift from robot_state payload."""
    robot_state = SimpleNamespace(
        pose_pitch_rad=0.3,
        pose_angle_rad=-0.4,
        lift_height_mm=55.0,
    )

    assert _extract_robot_telemetry_snapshot(None, None, robot_state) == (
        None,
        0.3,
        -0.4,
        55.0,
    )


def test_extract_robot_telemetry_snapshot_uses_filter_process() -> None:
    """Telemetry filter should be able to suppress noisy updates."""

    class FakeFilter:
        def __init__(self) -> None:
            self.calls = 0

        def process(self, telemetry):  # type: ignore[no-untyped-def]
            self.calls += 1
            if self.calls == 1:
                return telemetry
            return None

    telemetry = SimpleNamespace(
        roll_rad=0.2,
        pitch_rad=0.1,
        yaw_rad=-0.3,
        lift_height_mm=44.0,
    )
    pyddlvector = SimpleNamespace(extract_robot_telemetry=lambda _state: telemetry)
    telemetry_filter = FakeFilter()

    first = _extract_robot_telemetry_snapshot(pyddlvector, telemetry_filter, object())
    second = _extract_robot_telemetry_snapshot(pyddlvector, telemetry_filter, object())

    assert first == (0.2, 0.1, -0.3, 44.0)
    assert second == (None, None, None, None)


def test_validate_connection_sets_firmware_version() -> None:
    """Setup validation should preload firmware for device info registration."""
    import asyncio

    coordinator = object.__new__(VectorCoordinator)
    coordinator.firmware_version = None

    client = object()
    messaging = object()

    async def _fake_get_client():
        return client, messaging

    async def _fake_read_battery_state(_client, _messaging):  # type: ignore[no-untyped-def]
        return 3.9, "nominal", False

    async def _fake_read_firmware_version(_client, _messaging):  # type: ignore[no-untyped-def]
        return "2.1.3"

    coordinator._async_get_client = _fake_get_client  # type: ignore[attr-defined]
    coordinator._async_read_battery_state = _fake_read_battery_state  # type: ignore[attr-defined]
    coordinator._async_read_firmware_version = _fake_read_firmware_version  # type: ignore[attr-defined]

    asyncio.run(coordinator.async_validate_connection())

    assert coordinator.firmware_version == "2.1.3"


def test_is_unauthenticated_error_from_string() -> None:
    """Authentication failures should be recognized from exception text."""
    err = RuntimeError(
        "status = StatusCode.UNAUTHENTICATED details = Received http2 header with status: 401"
    )
    assert _is_unauthenticated_error(err) is True


def test_resolve_provision_mode_wirepod_by_default() -> None:
    """Without credentials, serial still produces wire-pod mode."""
    assert (
        _resolve_provision_mode(serial="00abc123", email=None, password=None)
        == "wirepod"
    )


def test_resolve_provision_mode_official_with_all_credentials() -> None:
    """When email/password/serial are present we should use official mode."""
    assert (
        _resolve_provision_mode(
            serial="00abc123",
            email="user@example.com",
            password="secret",
        )
        == "official"
    )


def test_resolve_provision_mode_rejects_partial_credentials() -> None:
    """Email/password must be supplied together."""
    try:
        _resolve_provision_mode(
            serial="00abc123",
            email="user@example.com",
            password=None,
        )
    except ValueError as err:
        assert "email and password" in str(err).lower()
    else:
        raise AssertionError("Expected ValueError for partial official credentials")


def test_resolve_provision_mode_rejects_missing_serial_in_official_mode() -> None:
    """Serial is required in all modes."""
    try:
        _resolve_provision_mode(
            serial=None,
            email="user@example.com",
            password="secret",
        )
    except ValueError as err:
        assert "serial" in str(err).lower()
    else:
        raise AssertionError("Expected ValueError when official mode misses serial")


def test_resolve_provision_mode_rejects_missing_serial_in_wirepod_mode() -> None:
    """Wire-pod mode also requires serial."""
    try:
        _resolve_provision_mode(
            serial=None,
            email=None,
            password=None,
        )
    except ValueError as err:
        assert "serial" in str(err).lower()
    else:
        raise AssertionError("Expected ValueError when wire-pod mode misses serial")


def test_trigger_quick_action_rejects_unknown_action() -> None:
    coordinator = object.__new__(VectorCoordinator)

    try:
        import asyncio

        asyncio.run(coordinator.async_trigger_quick_action("unknown_action"))
    except ValueError as err:
        assert "unsupported quick action" in str(err).lower()
    else:
        raise AssertionError("Expected ValueError for unsupported quick action")


def test_trigger_quick_action_falls_back_to_unary_path_when_stub_lacks_rpc() -> None:
    import asyncio

    coordinator = object.__new__(VectorCoordinator)

    class FakeStub:
        pass

    class FakeClient:
        def __init__(self) -> None:
            self.stub = FakeStub()
            self.unary_calls: list[str] = []

        async def unary_unary(self, path: str, request, **kwargs):  # type: ignore[no-untyped-def]
            del kwargs
            self.unary_calls.append(path)
            assert request.intent == "intent_system_sleep"
            return object()

    class FakeProtocol:
        class AppIntentRequest:
            def __init__(self, *, intent: str) -> None:
                self.intent = intent

            @staticmethod
            def SerializeToString(_request):  # type: ignore[no-untyped-def]
                return b""

        class AppIntentResponse:
            @staticmethod
            def FromString(_payload: bytes):  # type: ignore[no-untyped-def]
                return object()

    client = FakeClient()
    messaging = SimpleNamespace(protocol=FakeProtocol)

    async def _fake_get_client():
        return client, messaging

    coordinator._async_get_client = _fake_get_client  # type: ignore[attr-defined]

    asyncio.run(coordinator.async_trigger_quick_action("sleep"))
    assert client.unary_calls == [
        "/Anki.Vector.external_interface.ExternalInterface/AppIntent"
    ]


def test_say_text_uses_behavior_control_before_sending_request() -> None:
    import asyncio

    coordinator = object.__new__(VectorCoordinator)

    class FakeSayTextRequest:
        def __init__(self, **kwargs):  # type: ignore[no-untyped-def]
            self.kwargs = kwargs

    class FakeControlRequest:
        DEFAULT = 20
        OVERRIDE_BEHAVIORS = 10
        RESERVE_CONTROL = 30

        def __init__(self, *, priority: int) -> None:
            self.priority = priority

    class FakeBehaviorControlRequest:
        def __init__(
            self,
            *,
            control_request=None,  # type: ignore[no-untyped-def]
            control_release=None,  # type: ignore[no-untyped-def]
        ):
            self.control_request = control_request
            self.control_release = control_release

    class FakeControlRelease:
        pass

    class FakeResponse:
        def WhichOneof(self, _name: str) -> str:
            return "control_granted_response"

    class FakeStream:
        def __init__(self) -> None:
            self.write_calls = 0

        async def write(self, _request):  # type: ignore[no-untyped-def]
            self.write_calls += 1
            return None

        async def read(self):  # type: ignore[no-untyped-def]
            return FakeResponse()

        async def done_writing(self) -> None:
            return None

        def cancel(self) -> None:
            return None

    class FakeStub:
        def BehaviorControl(self, timeout):  # type: ignore[no-untyped-def]
            assert timeout == 10.0
            return FakeStream()

    class FakeClient:
        def __init__(self) -> None:
            self.stub = FakeStub()
            self.say_text_calls = 0
            self.last_request = None

        async def rpc(self, method_name: str, request, timeout):  # type: ignore[no-untyped-def]
            assert method_name == "SayText"
            assert timeout == 10.0
            assert isinstance(request, FakeSayTextRequest)
            self.say_text_calls += 1
            self.last_request = request
            return object()

    class FakeProtocol:
        SayTextRequest = FakeSayTextRequest
        ControlRequest = FakeControlRequest
        BehaviorControlRequest = FakeBehaviorControlRequest
        ControlRelease = FakeControlRelease

    client = FakeClient()
    messaging = SimpleNamespace(protocol=FakeProtocol)

    async def _fake_get_client():
        return client, messaging

    coordinator._async_get_client = _fake_get_client  # type: ignore[attr-defined]

    asyncio.run(coordinator.async_say_text(text="Hej Vector", pitch_scalar=0.4))
    assert client.say_text_calls == 1
    assert client.last_request is not None
    assert client.last_request.kwargs.get("pitch_scalar") == 0.4


def test_say_text_retries_after_sleep_when_control_not_granted() -> None:
    import asyncio

    coordinator = object.__new__(VectorCoordinator)
    coordinator.current_activity = "sleeping"

    class FakeSayTextRequest:
        def __init__(self, **kwargs):  # type: ignore[no-untyped-def]
            self.kwargs = kwargs

    class FakeControlRequest:
        DEFAULT = 20

    class FakeProtocol:
        SayTextRequest = FakeSayTextRequest
        ControlRequest = FakeControlRequest

    class FakeStub:
        BehaviorControl = object()

    class FakeClient:
        def __init__(self) -> None:
            self.stub = FakeStub()

    client = FakeClient()
    messaging = SimpleNamespace(protocol=FakeProtocol)

    async def _fake_get_client():
        return client, messaging

    calls = {"attempts": 0}

    async def _fake_say_text_with_control(*_args, **_kwargs):
        calls["attempts"] += 1
        if calls["attempts"] == 1:
            raise ValueError("Vector did not grant behavior control for SayText")
        return None

    async def _wake_then_ready(*, timeout: float):  # noqa: ARG001
        coordinator.current_activity = "idle"
        return True

    coordinator._async_get_client = _fake_get_client  # type: ignore[attr-defined]
    coordinator._async_say_text_with_behavior_control = (  # type: ignore[attr-defined]
        _fake_say_text_with_control
    )
    coordinator._async_wait_until_awake_for_say_text = _wake_then_ready  # type: ignore[attr-defined]

    asyncio.run(coordinator.async_say_text(text="Hej Vector"))
    assert calls["attempts"] == 2
