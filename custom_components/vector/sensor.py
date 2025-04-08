"""Vector robot sensors."""

from __future__ import annotations

import logging
from collections.abc import Callable
from dataclasses import dataclass
from enum import Enum

from homeassistant.components.sensor import (
    ENTITY_ID_FORMAT,
    RestoreSensor,
    SensorDeviceClass,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import STATE_UNKNOWN, EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.util import slugify as util_slugify

from .base import VectorBase, VectorBaseEntityDescription
from .const import (
    DOMAIN,
    ICON_DISTANCE,
    ICON_ROBOT,
    ICON_STATS,
    LANG_BATTERY,
    LANG_LIFETIME,
    LANG_STATE,
    LENGTH_CENTIMETERS,
    STATE_ACCEL,
    STATE_ALIVE_PET_MS,
    STATE_ALIVE_SENSOR_SCORE,
    STATE_ALIVE_TRIGGERWORDS,
    STATE_CAMERA_ENABLED,
    STATE_CARRYING_OBJECT,
    STATE_FIRMWARE_VERSION,
    STATE_GYRO,
    STATE_HEAD_TRACKING_ID,
    STATE_LIFT_HEIGHT,
    STATE_ROBOT_BATTERY_VOLTS,
    STATE_ROBOT_IS_CHARGNING,
    STATE_ROBOT_IS_ON_CHARGER,
    STATE_ROBOT_SUGGESTED_CHARGE,
    STATE_STIMULATION,
    UPDATE_SIGNAL,
)
from .helpers import States
from .mappings import ICONS

_LOGGER = logging.getLogger(__name__)


@dataclass
class VectorSensorEntityDescription(SensorEntityDescription):
    """Describes a Vector sensor."""

    value_fn: Callable[[States]] | str | None = None
    attribute_fn: Callable[[States]] | str | None = None
    update_signal: str | None = None


SENSORS = [
    VectorSensorEntityDescription(
        key="battery_voltage",
        name="Battery Voltage",
        device_class=SensorDeviceClass.VOLTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        entity_category=EntityCategory.DIAGNOSTIC,
        icon=ICONS[ICON_ROBOT],
        native_unit_of_measurement="V",
        value_fn=lambda states: (
            states.robot_battery_attributes(STATE_ROBOT_BATTERY_VOLTS)
            if not states.robot_battery_state() == STATE_UNKNOWN
            else STATE_UNKNOWN
        ),
    ),
    VectorSensorEntityDescription(
        key="battery_state",
        name="Battery",
        device_class=SensorDeviceClass.BATTERY,
        state_class=SensorStateClass.MEASUREMENT,
        entity_category=None,
        native_unit_of_measurement="%",
        value_fn=lambda states: (
            states.robot_battery_percentage
            if not states.robot_battery_state() == STATE_UNKNOWN
            else STATE_UNKNOWN
        ),
        attribute_fn=lambda attributes: attributes.get_robot_battery_attributes(
            {
                STATE_ROBOT_IS_CHARGNING: "charging",
            }
        ),
    ),
    VectorSensorEntityDescription(
        key="battery_charge_time",
        name="Suggested Charge Time",
        device_class=SensorDeviceClass.DURATION,
        state_class=SensorStateClass.MEASUREMENT,
        entity_category=EntityCategory.DIAGNOSTIC,
        icon=ICONS[ICON_ROBOT],
        native_unit_of_measurement="s",
        suggested_display_precision=1,
        value_fn=lambda states: (
            states.robot_battery_attributes(STATE_ROBOT_SUGGESTED_CHARGE)
            if not states.robot_battery_state() == STATE_UNKNOWN
            else STATE_UNKNOWN
        ),
    ),
    VectorSensorEntityDescription(
        key="age",
        name="Age",
        device_class=None,
        state_class=None,
        entity_category=EntityCategory.DIAGNOSTIC,
        icon=ICONS[ICON_STATS],
        value_fn=lambda states: (
            states.robot_age
            if not isinstance(states.robot_age, type(None))
            else STATE_UNKNOWN
        ),
        attribute_fn=lambda attributes: attributes.get_robot_attributes(
            {
                STATE_ALIVE_TRIGGERWORDS: "reacts_to_triggerword",
                STATE_ALIVE_PET_MS: "seconds_petted",
                STATE_ALIVE_SENSOR_SCORE: "sensory_score",
            }
        ),
    ),
    VectorSensorEntityDescription(
        key="driven_distance",
        name="Distance driven",
        device_class=SensorDeviceClass.DISTANCE,
        state_class=SensorStateClass.TOTAL_INCREASING,
        entity_category=EntityCategory.DIAGNOSTIC,
        icon=ICONS[ICON_DISTANCE],
        value_fn=lambda states: (
            states.robot_distance
            if not isinstance(states.robot_age, type(None))
            else STATE_UNKNOWN
        ),
        native_unit_of_measurement=LENGTH_CENTIMETERS,
    ),
    VectorSensorEntityDescription(
        key="vector_status",
        name="Status",
        device_class=None,
        state_class=None,
        entity_category=None,
        icon=ICONS[ICON_ROBOT],
        translation_key="vector_status",
        update_signal=UPDATE_SIGNAL.format("robot", "{}", "robot_status"),
        value_fn=lambda states: (
            states.robot_state
            if not states.robot_state == STATE_UNKNOWN
            else STATE_UNKNOWN
        ),
        attribute_fn=lambda attributes: attributes.get_robot_attributes(
            {
                STATE_FIRMWARE_VERSION: "firmware_version",
                STATE_STIMULATION: "stimulation",
                STATE_CARRYING_OBJECT: "carrying_object_id",
                STATE_HEAD_TRACKING_ID: "head_tracking_object_id",
                STATE_CAMERA_ENABLED: "camera_stream_enabled",
                STATE_GYRO: "gyro",
                STATE_ACCEL: "acceleration",
                STATE_LIFT_HEIGHT: "lift_height_mm",
            }
        ),
    ),
]


class VectorBaseSensorEntity(VectorBase, RestoreSensor):
    """Defines a Vector sensor."""

    entity_description: VectorSensorEntityDescription
    # _attr_should_poll: bool = True

    def __init__(
        self,
        description: VectorSensorEntityDescription,
        coordinator,
    ):
        """Initialize a base sensor."""
        from .coordinator import (  # pylint: disable=import-outside-toplevel
            VectorDataUpdateCoordinator,
        )

        RestoreSensor.__init__(coordinator)
        VectorBase.__init__(self, coordinator)

        self.entity_description = description

        self._attr_unique_id = util_slugify(
            f"{self.entry.unique_id}-sensor-{self.entity_description.name}"
        )

        self.entity_id = ENTITY_ID_FORMAT.format(
            util_slugify(f"{self.coordinator.vector_name}_{description.name}")
        )

        self._attr_icon = description.icon

        self._attr_extra_state_attributes = {}
        self._attr_name = self.entity_description.name

        if not isinstance(self.entity_description.update_signal, type(None)):
            update = self.entity_description.update_signal.format(self.coordinator.name)
            _LOGGER.debug("Update signal: %s", update)
            async_dispatcher_connect(
                self.hass,
                update,
                self._handle_coordinator_update,
            )

        self._handle_coordinator_update()

    async def async_added_to_hass(self) -> None:
        """Register entity for updates from API."""
        await super().async_added_to_hass()

    def _handle_coordinator_update(self) -> None:
        """Update the entity."""
        _LOGGER.debug("Refresh sensor data for '%s'", self.entity_description.name)
        state = self.entity_description.value_fn(self.coordinator.states)
        _LOGGER.debug(
            " - Updating sensor state: '%s'",
            state,
        )
        self._attr_native_value = str(state)

        try:
            _LOGGER.debug(
                " - Setting attributes: %s",
                self.entity_description.attribute_fn(self.coordinator.states),
            )
            self._attr_extra_state_attributes.update(
                self.entity_description.attribute_fn(self.coordinator.states)
            )
        except:  # pylint: disable=bare-except
            self._attr_extra_state_attributes.clear()

        # self.async_write_ha_state()
        self.schedule_update_ha_state()


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Add Vector sensor entries."""
    coordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]

    sensor_entities = []
    for sensor in SENSORS:
        entity = VectorBaseSensorEntity(sensor, coordinator)
        _LOGGER.debug(
            "Adding sensor '%s' with entity_id '%s'", sensor.name, entity.entity_id
        )
        sensor_entities.append(entity)

    async_add_entities(sensor_entities)
