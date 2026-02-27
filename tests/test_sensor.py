"""Tests for Vector sensor entities."""

from __future__ import annotations

from types import SimpleNamespace

from custom_components.vector.const import (
    CONF_HOST,
    CONF_ROBOT_NAME,
    CONF_SERIAL,
    DOMAIN,
)
from custom_components.vector.sensor import (
    VectorBatterySensor,
    VectorCurrentActivitySensor,
    VectorDaysAliveSensor,
    VectorDistanceMovedSensor,
    VectorReactedToTriggerWordSensor,
    VectorSecondsPettedSensor,
    VectorStimulationSensor,
)


class FakeCoordinator:
    """Simple coordinator stub for entity tests."""

    def __init__(
        self,
        current_activity: str,
        battery_percent: int | None = None,
        battery_volts: float | None = None,
        battery_level: str = "unknown",
        is_charging: bool | None = None,
        firmware_version: str | None = None,
        robot_serial: str | None = None,
        days_alive: int | None = None,
        reacted_to_trigger_word: int | None = None,
        seconds_petted: int | None = None,
        distance_moved_cm: int | None = None,
        stimulation_value: float | None = None,
        stimulation_velocity: float | None = None,
        stimulation_accel: float | None = None,
        stimulation_value_before_event: float | None = None,
        stimulation_min_value: float | None = None,
        stimulation_max_value: float | None = None,
        stimulation_emotion_events: tuple[str, ...] = (),
    ) -> None:
        """Initialize coordinator stub."""
        self.current_activity = current_activity
        self.battery_percent = battery_percent
        self.battery_volts = battery_volts
        self.battery_level = battery_level
        self.is_charging = is_charging
        self.firmware_version = firmware_version
        self.robot_serial = robot_serial
        self.days_alive = days_alive
        self.reacted_to_trigger_word = reacted_to_trigger_word
        self.seconds_petted = seconds_petted
        self.distance_moved_cm = distance_moved_cm
        self.stimulation_value = stimulation_value
        self.stimulation_velocity = stimulation_velocity
        self.stimulation_accel = stimulation_accel
        self.stimulation_value_before_event = stimulation_value_before_event
        self.stimulation_min_value = stimulation_min_value
        self.stimulation_max_value = stimulation_max_value
        self.stimulation_emotion_events = stimulation_emotion_events

    def async_add_listener(self, update_callback):
        """Match DataUpdateCoordinator listener contract."""
        del update_callback
        return lambda: None


def _entry(data: dict[str, str], entry_id: str = "entry-1") -> SimpleNamespace:
    """Create a config entry stub."""
    return SimpleNamespace(data=data, entry_id=entry_id)


def test_current_activity_sensor_native_value() -> None:
    """Sensor should expose coordinator activity."""
    coordinator = FakeCoordinator(current_activity="docking")
    entry = _entry({CONF_ROBOT_NAME: "Vector-ABCD", CONF_HOST: "192.168.1.10"})

    entity = VectorCurrentActivitySensor(coordinator, entry)

    assert entity.native_value == "docking"


def test_current_activity_sensor_options_include_new_tracker_states() -> None:
    """Enum options must include normalized states emitted by activity tracker."""
    coordinator = FakeCoordinator(current_activity="exploring_from_charger")
    entry = _entry({CONF_ROBOT_NAME: "Vector-ABCD", CONF_HOST: "192.168.1.10"})

    entity = VectorCurrentActivitySensor(coordinator, entry)

    assert "falling" in entity.options
    assert "cliff_detected" in entity.options
    assert "being_held" in entity.options
    assert "picked_up" in entity.options
    assert "charging_on_charger" in entity.options
    assert "exploring_from_charger" in entity.options
    assert "looking_for_faces" in entity.options
    assert "looking_for_charger" in entity.options
    assert "looking_for_cubes" in entity.options
    assert "looking_for_objects" in entity.options
    assert "picking_or_placing_object" in entity.options
    assert "animating" in entity.options
    assert "button_pressed" in entity.options
    assert "ready" in entity.options


def test_current_activity_sensor_device_identifier_prefers_serial() -> None:
    """Device identifiers should prefer robot serial when available."""
    coordinator = FakeCoordinator(current_activity="idle")
    entry = _entry(
        {
            CONF_ROBOT_NAME: "Vector-ABCD",
            CONF_HOST: "vector.local",
            CONF_SERIAL: "00a1",
        }
    )

    entity = VectorCurrentActivitySensor(coordinator, entry)

    assert entity.device_info["identifiers"] == {(DOMAIN, "00a1")}


def test_battery_voltage_sensor_value_and_attributes() -> None:
    """Battery sensor should expose volts + status attributes."""
    coordinator = FakeCoordinator(
        current_activity="idle",
        battery_percent=62,
        battery_volts=3.92,
        battery_level="nominal",
        is_charging=True,
    )
    entry = _entry({CONF_ROBOT_NAME: "Vector-ABCD", CONF_HOST: "192.168.1.10"})

    entity = VectorBatterySensor(coordinator, entry)

    assert entity.native_value == 62
    assert entity.extra_state_attributes == {
        "battery_voltage": 3.92,
        "battery_level": "nominal",
        "charging": True,
    }


def test_stimulation_sensor_value_and_attributes() -> None:
    """Stimulation sensor should expose value + stimulation attributes."""
    coordinator = FakeCoordinator(
        current_activity="idle",
        stimulation_value=0.42,
        stimulation_velocity=0.11,
        stimulation_accel=-0.03,
        stimulation_value_before_event=0.39,
        stimulation_min_value=0.0,
        stimulation_max_value=1.0,
        stimulation_emotion_events=("Frustrated", "Excited"),
    )
    entry = _entry({CONF_ROBOT_NAME: "Vector-ABCD", CONF_HOST: "192.168.1.10"})

    entity = VectorStimulationSensor(coordinator, entry)

    assert entity.native_value == 0.42
    assert entity.entity_registry_enabled_default is False
    assert entity.extra_state_attributes == {
        "velocity": 0.11,
        "accel": -0.03,
        "value_before_event": 0.39,
        "min_value": 0.0,
        "max_value": 1.0,
        "emotion_events": ["Frustrated", "Excited"],
    }


def test_stats_sensors_values() -> None:
    """Lifetime stats sensors should expose coordinator values."""
    coordinator = FakeCoordinator(
        current_activity="idle",
        days_alive=529,
        reacted_to_trigger_word=786,
        seconds_petted=2413,
        distance_moved_cm=73391,
    )
    entry = _entry({CONF_ROBOT_NAME: "Vector-ABCD", CONF_HOST: "192.168.1.10"})

    assert VectorDaysAliveSensor(coordinator, entry).native_value == 529
    assert VectorReactedToTriggerWordSensor(coordinator, entry).native_value == 786
    assert VectorSecondsPettedSensor(coordinator, entry).native_value == 2413
    assert VectorDistanceMovedSensor(coordinator, entry).native_value == 73391


def test_stats_sensors_are_disabled_by_default() -> None:
    """Stats sensors should be disabled by default in entity registry."""
    coordinator = FakeCoordinator(current_activity="idle")
    entry = _entry({CONF_ROBOT_NAME: "Vector-ABCD", CONF_HOST: "192.168.1.10"})

    assert (
        VectorDaysAliveSensor(coordinator, entry).entity_registry_enabled_default
        is False
    )
    assert (
        VectorReactedToTriggerWordSensor(
            coordinator, entry
        ).entity_registry_enabled_default
        is False
    )
    assert (
        VectorSecondsPettedSensor(coordinator, entry).entity_registry_enabled_default
        is False
    )
    assert (
        VectorDistanceMovedSensor(coordinator, entry).entity_registry_enabled_default
        is False
    )


def test_device_info_uses_anki_for_generation_1_serials() -> None:
    """Serials starting with 00 should map to Anki / hw generation 1.0."""
    coordinator = FakeCoordinator(current_activity="idle", firmware_version="2.1.3")
    entry = _entry(
        {
            CONF_ROBOT_NAME: "Vector-A1B2",
            CONF_HOST: "192.168.1.10",
            CONF_SERIAL: "00a1b2c3",
        }
    )

    entity = VectorCurrentActivitySensor(coordinator, entry)

    assert entity.device_info["manufacturer"] == "Anki"
    assert entity.device_info["hw_version"] == "1.0"
    assert entity.device_info["sw_version"] == "2.1.3"


def test_device_info_uses_ddl_for_generation_2_serials() -> None:
    """Serials not starting with 00 should map to DDL / hw generation 2.0."""
    coordinator = FakeCoordinator(current_activity="idle")
    entry = _entry(
        {
            CONF_ROBOT_NAME: "Vector-Z9Y8",
            CONF_HOST: "192.168.1.11",
            CONF_SERIAL: "10deadbeef",
        }
    )

    entity = VectorCurrentActivitySensor(coordinator, entry)

    assert entity.device_info["manufacturer"] == "Digital Dream Labs"
    assert entity.device_info["hw_version"] == "2.0"


def test_device_info_handles_none_serial_without_false_ddl() -> None:
    """None serial values should not become string 'None' and misclassify vendor."""
    coordinator = FakeCoordinator(current_activity="idle", robot_serial="00ff00aa")
    entry = _entry(
        {
            CONF_ROBOT_NAME: "Vector-T3X9",
            CONF_HOST: "192.168.1.12",
            CONF_SERIAL: None,
        }
    )

    entity = VectorCurrentActivitySensor(coordinator, entry)

    assert entity.device_info["manufacturer"] == "Anki"
    assert entity.device_info["hw_version"] == "1.0"


def test_device_info_with_missing_serial_is_unknown_generation() -> None:
    """Missing serial should not default to generation 2.0."""
    coordinator = FakeCoordinator(current_activity="idle", robot_serial=None)
    entry = _entry(
        {
            CONF_ROBOT_NAME: "Vector-T3X9",
            CONF_HOST: "192.168.1.12",
        }
    )

    entity = VectorCurrentActivitySensor(coordinator, entry)

    assert entity.device_info["manufacturer"] == "Anki / Digital Dream Labs"
    assert entity.device_info["hw_version"] is None
