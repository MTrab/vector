"""Sensor platform for Vector integration."""

from __future__ import annotations

import math

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import DEGREE, PERCENTAGE, UnitOfLength, UnitOfTime
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .coordinator import VectorCoordinator
from .entity import VectorEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Vector sensors from a config entry."""
    coordinator: VectorCoordinator = entry.runtime_data["coordinator"]
    async_add_entities(
        [
            VectorCurrentActivitySensor(coordinator, entry),
            VectorStimulationSensor(coordinator, entry),
            VectorBatterySensor(coordinator, entry),
            VectorOrientationRollSensor(coordinator, entry),
            VectorOrientationPitchSensor(coordinator, entry),
            VectorOrientationYawSensor(coordinator, entry),
            VectorLiftHeightSensor(coordinator, entry),
            VectorDaysAliveSensor(coordinator, entry),
            VectorReactedToTriggerWordSensor(coordinator, entry),
            VectorSecondsPettedSensor(coordinator, entry),
            VectorDistanceMovedSensor(coordinator, entry),
        ]
    )


class VectorCurrentActivitySensor(VectorEntity, SensorEntity):
    """Current activity sensor for Vector."""

    _attr_has_entity_name = True
    _attr_translation_key = "current_activity"
    _attr_device_class = SensorDeviceClass.ENUM
    _attr_options = [
        "unknown",
        "falling",
        "cliff_detected",
        "being_held",
        "picked_up",
        "sleeping",
        "exploring",
        "exploring_from_charger",
        "looking_for_faces",
        "looking_for_charger",
        "looking_for_cubes",
        "looking_for_objects",
        "picking_or_placing_object",
        "button_pressed",
        "ready",
        # Backward-compatible fallback values used when tracker is unavailable.
        "moving",
        "being_touched",
        "carrying_object",
        "charging",
        "on_charger",
        "idle",
    ]
    _attr_icon = "mdi:robot"

    def __init__(self, coordinator: VectorCoordinator, entry: ConfigEntry) -> None:
        """Initialize current activity sensor."""
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{entry.entry_id}_current_activity"

    @property
    def native_value(self) -> str:
        """Return the robot's current activity."""
        return self.coordinator.current_activity


class VectorBatterySensor(VectorEntity, SensorEntity):
    """Battery sensor for Vector."""

    _attr_has_entity_name = True
    _attr_translation_key = "battery"
    _attr_icon = "mdi:battery"
    _attr_device_class = SensorDeviceClass.BATTERY
    _attr_native_unit_of_measurement = PERCENTAGE
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(self, coordinator: VectorCoordinator, entry: ConfigEntry) -> None:
        """Initialize battery voltage sensor."""
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{entry.entry_id}_battery"

    @property
    def native_value(self) -> int | None:
        """Return battery percentage value."""
        return self.coordinator.battery_percent

    @property
    def extra_state_attributes(self) -> dict[str, float | str | bool | None]:
        """Return battery metadata."""
        return {
            "battery_voltage": self.coordinator.battery_volts,
            "battery_level": self.coordinator.battery_level,
            "charging": self.coordinator.is_charging,
        }


class VectorStimulationSensor(VectorEntity, SensorEntity):
    """Stimulation sensor for Vector."""

    _attr_has_entity_name = True
    _attr_translation_key = "stimulation"
    _attr_icon = "mdi:heart-pulse"
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_entity_registry_enabled_default = False

    def __init__(self, coordinator: VectorCoordinator, entry: ConfigEntry) -> None:
        """Initialize stimulation sensor."""
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{entry.entry_id}_stimulation"

    @property
    def native_value(self) -> float | None:
        """Return stimulation value."""
        return self.coordinator.stimulation_value

    @property
    def extra_state_attributes(self) -> dict[str, float | list[str] | None]:
        """Return stimulation metadata."""
        return {
            "velocity": self.coordinator.stimulation_velocity,
            "accel": self.coordinator.stimulation_accel,
            "value_before_event": self.coordinator.stimulation_value_before_event,
            "min_value": self.coordinator.stimulation_min_value,
            "max_value": self.coordinator.stimulation_max_value,
            "emotion_events": list(self.coordinator.stimulation_emotion_events),
        }


class VectorOrientationRollSensor(VectorEntity, SensorEntity):
    """Robot roll orientation sensor in degrees."""

    _attr_has_entity_name = True
    _attr_translation_key = "orientation_roll"
    _attr_icon = "mdi:axis-x-rotate-clockwise"
    _attr_native_unit_of_measurement = DEGREE
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_entity_registry_enabled_default = False

    def __init__(self, coordinator: VectorCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{entry.entry_id}_orientation_roll"

    @property
    def native_value(self) -> float | None:
        value = self.coordinator.orientation_roll_rad
        if value is None:
            return None
        return math.degrees(value)


class VectorOrientationPitchSensor(VectorEntity, SensorEntity):
    """Robot pitch orientation sensor in degrees."""

    _attr_has_entity_name = True
    _attr_translation_key = "orientation_pitch"
    _attr_icon = "mdi:axis-y-rotate-clockwise"
    _attr_native_unit_of_measurement = DEGREE
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_entity_registry_enabled_default = False

    def __init__(self, coordinator: VectorCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{entry.entry_id}_orientation_pitch"

    @property
    def native_value(self) -> float | None:
        value = self.coordinator.orientation_pitch_rad
        if value is None:
            return None
        return math.degrees(value)


class VectorOrientationYawSensor(VectorEntity, SensorEntity):
    """Robot yaw orientation sensor in degrees."""

    _attr_has_entity_name = True
    _attr_translation_key = "orientation_yaw"
    _attr_icon = "mdi:axis-z-rotate-clockwise"
    _attr_native_unit_of_measurement = DEGREE
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_entity_registry_enabled_default = False

    def __init__(self, coordinator: VectorCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{entry.entry_id}_orientation_yaw"

    @property
    def native_value(self) -> float | None:
        value = self.coordinator.orientation_yaw_rad
        if value is None:
            return None
        return math.degrees(value)


class VectorLiftHeightSensor(VectorEntity, SensorEntity):
    """Robot lift height sensor in millimeters."""

    _attr_has_entity_name = True
    _attr_translation_key = "lift_height"
    _attr_icon = "mdi:elevator"
    _attr_native_unit_of_measurement = UnitOfLength.MILLIMETERS
    _attr_device_class = SensorDeviceClass.DISTANCE
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_entity_registry_enabled_default = False

    def __init__(self, coordinator: VectorCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{entry.entry_id}_lift_height"

    @property
    def native_value(self) -> float | None:
        return self.coordinator.lift_height_mm


class VectorDaysAliveSensor(VectorEntity, SensorEntity):
    """Days alive sensor for Vector."""

    _attr_has_entity_name = True
    _attr_translation_key = "days_alive"
    _attr_icon = "mdi:calendar-clock"
    _attr_state_class = SensorStateClass.TOTAL_INCREASING
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_entity_registry_enabled_default = False

    def __init__(self, coordinator: VectorCoordinator, entry: ConfigEntry) -> None:
        """Initialize days alive sensor."""
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{entry.entry_id}_days_alive"

    @property
    def native_value(self) -> int | None:
        """Return days alive."""
        return self.coordinator.days_alive


class VectorReactedToTriggerWordSensor(VectorEntity, SensorEntity):
    """Trigger word reaction count sensor."""

    _attr_has_entity_name = True
    _attr_translation_key = "reacted_to_trigger_word"
    _attr_icon = "mdi:microphone-message"
    _attr_state_class = SensorStateClass.TOTAL_INCREASING
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_entity_registry_enabled_default = False

    def __init__(self, coordinator: VectorCoordinator, entry: ConfigEntry) -> None:
        """Initialize reacted-to-trigger-word sensor."""
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{entry.entry_id}_reacted_to_trigger_word"

    @property
    def native_value(self) -> int | None:
        """Return number of trigger word reactions."""
        return self.coordinator.reacted_to_trigger_word


class VectorSecondsPettedSensor(VectorEntity, SensorEntity):
    """Seconds petted sensor for Vector."""

    _attr_has_entity_name = True
    _attr_translation_key = "seconds_petted"
    _attr_icon = "mdi:hand-heart"
    _attr_native_unit_of_measurement = UnitOfTime.SECONDS
    _attr_device_class = SensorDeviceClass.DURATION
    _attr_state_class = SensorStateClass.TOTAL_INCREASING
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_entity_registry_enabled_default = False

    def __init__(self, coordinator: VectorCoordinator, entry: ConfigEntry) -> None:
        """Initialize seconds petted sensor."""
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{entry.entry_id}_seconds_petted"

    @property
    def native_value(self) -> int | None:
        """Return cumulative seconds petted."""
        return self.coordinator.seconds_petted


class VectorDistanceMovedSensor(VectorEntity, SensorEntity):
    """Distance moved sensor for Vector."""

    _attr_has_entity_name = True
    _attr_translation_key = "distance_moved"
    _attr_icon = "mdi:map-marker-distance"
    _attr_native_unit_of_measurement = UnitOfLength.CENTIMETERS
    _attr_device_class = SensorDeviceClass.DISTANCE
    _attr_state_class = SensorStateClass.TOTAL_INCREASING
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_entity_registry_enabled_default = False

    def __init__(self, coordinator: VectorCoordinator, entry: ConfigEntry) -> None:
        """Initialize distance moved sensor."""
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{entry.entry_id}_distance_moved_cm"

    @property
    def native_value(self) -> int | None:
        """Return cumulative distance moved in centimeters."""
        return self.coordinator.distance_moved_cm
