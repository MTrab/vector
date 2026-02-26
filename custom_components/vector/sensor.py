"""Sensor platform for Vector integration."""

from __future__ import annotations

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import PERCENTAGE, UnitOfLength, UnitOfTime
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .coordinator import VectorCoordinator
from .entity import VectorEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Vector sensors from a config entry."""
    coordinator: VectorCoordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]
    async_add_entities(
        [
            VectorCurrentActivitySensor(coordinator, entry),
            VectorStimulationSensor(coordinator, entry),
            VectorBatterySensor(coordinator, entry),
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
        "sleeping",
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
