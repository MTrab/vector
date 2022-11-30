"""Vector robot sensors."""
from __future__ import annotations
from collections.abc import Callable
from dataclasses import dataclass, field
from enum import Enum, IntEnum

import logging

from homeassistant.components.sensor import (
    ENTITY_ID_FORMAT,
    RestoreSensor,
    SensorDeviceClass,
    SensorEntityDescription,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import STATE_UNKNOWN
from homeassistant.core import HomeAssistant
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.util import slugify as util_slugify

from .base import VectorBase, VectorBaseEntityDescription
from .const import (
    DOMAIN,
    ICON_CUBE,
    ICON_ROBOT,
    LANG_BATTERY,
    STATE_CUBE_BATTERY_VOLTS,
    STATE_CUBE_FACTORY_ID,
    STATE_CUBE_LAST_CONTACT,
    STATE_NO_DATA,
    STATE_ROBOT_BATTERY_VOLTS,
    STATE_ROBOT_IS_CHARGNING,
    STATE_ROBOT_IS_ON_CHARGER,
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


@dataclass
class VectorSensorEntityDescription(
    VectorBaseEntityDescription, SensorEntityDescription
):
    """Describes a Vector sensor."""

    sensor_type: VectorSensorType = VectorSensorType.STATE


SENSORS = [
    VectorSensorEntityDescription(
        key=VectorSensorFeature.BATTERY_ROBOT,
        name="Battery Level",
        device_class=SensorDeviceClass.BATTERY,
        icon=ICONS[ICON_ROBOT],
        sensor_type=VectorSensorType.BATTERY,
        translate_key=LANG_BATTERY,
        value_fn=lambda states: states.robot_battery_state()
        if not states.robot_battery_state() == STATE_UNKNOWN
        else STATE_NO_DATA,
        attribute_fn=lambda attributes: attributes.get_robot_battery_attributes(
            {
                STATE_ROBOT_BATTERY_VOLTS: "voltage",
                STATE_ROBOT_IS_CHARGNING: "charging",
                STATE_ROBOT_IS_ON_CHARGER: "on_charger",
            }
        ),
    ),
    VectorSensorEntityDescription(
        key=VectorSensorFeature.BATTERY_CUBE,
        name="Cube battery Level",
        device_class=SensorDeviceClass.BATTERY,
        icon=ICONS[ICON_CUBE],
        sensor_type=VectorSensorType.BATTERY,
        translate_key=LANG_BATTERY,
        value_fn=lambda states: states.cube_battery_state()
        if not states.cube_battery_state() == STATE_UNKNOWN
        else STATE_NO_DATA,
        attribute_fn=lambda attributes: attributes.cube_battery_attributes(
            {
                STATE_CUBE_BATTERY_VOLTS: "voltage",
                STATE_CUBE_FACTORY_ID: "mac_address",
                STATE_CUBE_LAST_CONTACT: "last_contact",
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

        self.coordinator: VectorDataUpdateCoordinator = coordinator
        self.entry: ConfigEntry = coordinator.entry
        self.hass: HomeAssistant = coordinator.hass
        super().__init__(coordinator)

        self.entity_description = description

        self._attr_unique_id = util_slugify(
            f"{self.entry.unique_id}-sensor-{self.entity_description.name}"
        )

        self.entity_id = ENTITY_ID_FORMAT.format(
            util_slugify(f"{self.coordinator.vector_name}_{description.name}")
        )

        self._attr_icon = description.icon

        self._attr_extra_state_attributes = {}
        self._attr_native_value = self.entity_description.start_value
        self._attr_device_class = f"{DOMAIN}__{self.entity_description.translate_key}"
        self._attr_name = self.entity_description.name

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
        self._attr_native_value = self.entity_description.value_fn(
            self.coordinator.states
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
