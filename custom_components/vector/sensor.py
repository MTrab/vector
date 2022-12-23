"""Vector robot sensors."""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum, IntEnum

import logging

from homeassistant.components.sensor import (
    ENTITY_ID_FORMAT,
    RestoreSensor,
    SensorDeviceClass,
    SensorEntityDescription,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import STATE_UNKNOWN, LENGTH_CENTIMETERS
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.util import slugify as util_slugify
from homeassistant.helpers.dispatcher import async_dispatcher_connect

from .base import VectorBase, VectorBaseEntityDescription
from .const import (
    DOMAIN,
    ICON_DISTANCE,
    ICON_ROBOT,
    ICON_STATS,
    LANG_BATTERY,
    LANG_LIFETIME,
    LANG_STATE,
    STATE_ALIVE_PET_MS,
    STATE_ALIVE_SENSOR_SCORE,
    STATE_ALIVE_TRIGGERWORDS,
    STATE_ROBOT_BATTERY_VOLTS,
    STATE_ROBOT_IS_CHARGNING,
    STATE_ROBOT_IS_ON_CHARGER,
    UPDATE_SIGNAL,
)
from .mappings import ICONS


_LOGGER = logging.getLogger(__name__)


class VectorSensorType(IntEnum):
    """Vector sensor types."""

    BATTERY = 0
    STATE = 1
    FACE = 2


class VectorSensorFeature(Enum):
    """Different battery sensor types."""

    BATTERY_ROBOT = "battery_robot"
    BATTERY_CUBE = "battery_cube"
    STATUS = "status"
    OBSERVATION = "observation"
    FACE = "face"
    LIFETIME_STATS = "lifetime_stats"
    DRIVEN_DISTANCE = "driven_distance"


@dataclass
class VectorSensorEntityDescription(
    VectorBaseEntityDescription, SensorEntityDescription
):
    """Describes a Vector sensor."""

    sensor_type: VectorSensorType = VectorSensorType.STATE
    update_signal: str | None = None


SENSORS = [
    VectorSensorEntityDescription(
        key=VectorSensorFeature.BATTERY_ROBOT,
        name="Battery Level",
        device_class=SensorDeviceClass.BATTERY,
        icon=ICONS[ICON_ROBOT],
        sensor_type=VectorSensorType.BATTERY,
        translation_key=LANG_BATTERY,
        value_fn=lambda states: states.robot_battery_state()
        if not states.robot_battery_state() == STATE_UNKNOWN
        else STATE_UNKNOWN,
        attribute_fn=lambda attributes: attributes.get_robot_battery_attributes(
            {
                STATE_ROBOT_BATTERY_VOLTS: "voltage",
                STATE_ROBOT_IS_CHARGNING: "charging",
                STATE_ROBOT_IS_ON_CHARGER: "on_charger",
            }
        ),
    ),
    VectorSensorEntityDescription(
        key=VectorSensorFeature.LIFETIME_STATS,
        name="Age",
        device_class=SensorDeviceClass.DURATION,
        icon=ICONS[ICON_STATS],
        sensor_type=VectorSensorType.STATE,
        translation_key=LANG_LIFETIME,
        value_fn=lambda states: states.robot_age
        if not states.robot_age == STATE_UNKNOWN
        else STATE_UNKNOWN,
        attribute_fn=lambda attributes: attributes.get_robot_attributes(
            {
                STATE_ALIVE_TRIGGERWORDS: "reacts_to_triggerword",
                STATE_ALIVE_PET_MS: "seconds_petted",
                STATE_ALIVE_SENSOR_SCORE: "sensory_score",
            }
        ),
    ),
    VectorSensorEntityDescription(
        key=VectorSensorFeature.DRIVEN_DISTANCE,
        name="Distance driven",
        device_class=SensorDeviceClass.DISTANCE,
        icon=ICONS[ICON_DISTANCE],
        sensor_type=VectorSensorType.STATE,
        translation_key=LANG_LIFETIME,
        value_fn=lambda states: states.robot_distance
        if not states.robot_age == STATE_UNKNOWN
        else STATE_UNKNOWN,
        native_unit_of_measurement=LENGTH_CENTIMETERS,
    ),
    VectorSensorEntityDescription(
        key=VectorSensorFeature.STATUS,
        name="Status",
        icon=ICONS[ICON_ROBOT],
        sensor_type=VectorSensorType.STATE,
        translation_key=LANG_STATE,
        update_signal=UPDATE_SIGNAL.format("robot", "{}", "robot_status"),
        value_fn=lambda states: states.robot_state
        if not states.robot_state == STATE_UNKNOWN
        else STATE_UNKNOWN,
        # attribute_fn=lambda attributes: attributes.get_robot_attributes(
        #     {
        #         STATE_FIRMWARE_VERSION: "firmware_version",
        #         STATE_STIMULATION: "stimulation",
        #         STATE_CARRYING_OBJECT: "carrying_object_id",
        #         STATE_HEAD_TRACKING_ID: "head_tracking_object_id",
        #         STATE_CAMERA_ENABLED: "camera_stream_enabled",
        #         STATE_GYRO: "gyro",
        #         STATE_ACCEL: "acceleration",
        #         STATE_LIFT_HEIGHT: "lift_height_mm",
        #     }
        # ),
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

        self.coordinator: VectorDataUpdateCoordinator = coordinator
        self.entry: ConfigEntry = coordinator.entry
        self.hass: HomeAssistant = coordinator.hass

        self.entity_description = description

        self._attr_unique_id = util_slugify(
            f"{self.entry.unique_id}-sensor-{self.entity_description.name}"
        )

        self.entity_id = ENTITY_ID_FORMAT.format(
            util_slugify(f"{self.coordinator.vector_name}_{description.name}")
        )

        self._attr_icon = description.icon

        self._attr_extra_state_attributes = {}
        # self._attr_native_value = self.entity_description.start_value
        self._attr_device_class = f"{DOMAIN}__{self.entity_description.translation_key}"
        self._attr_name = self.entity_description.name
        if not isinstance(self.entity_description.update_signal, type(None)):
            update = self.entity_description.update_signal.format(self.coordinator.name)
            _LOGGER.debug("Update signal: %s", update)
            async_dispatcher_connect(
                self.hass,
                update,
                self._handle_coordinator_update,
            )

    async def async_added_to_hass(self) -> None:
        """Register entity for updates from API."""
        await super().async_added_to_hass()

    def _handle_coordinator_update(self) -> None:
        """Update the entity."""
        _LOGGER.debug("Refresh sensor data for '%s'", self.entity_description.name)
        _LOGGER.debug(
            " - Updating sensor state: '%s'",
            self.entity_description.value_fn(self.coordinator.states),
        )
        self._attr_native_value = str(
            self.entity_description.value_fn(self.coordinator.states)
        )

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

        self.async_write_ha_state()


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
