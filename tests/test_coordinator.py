"""Tests for Vector coordinator behavior."""

from __future__ import annotations

from types import SimpleNamespace

from custom_components.vector.coordinator import (
    _battery_percentage_from_wirepod_curve,
    _derive_activity_from_robot_state,
    _normalize_stimulation_snapshot,
    _normalize_battery_level_name,
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
