"""Adds binary_sensors to the device."""

from __future__ import annotations

import logging
from collections.abc import Callable
from dataclasses import dataclass

from homeassistant.components.binary_sensor import (
    ENTITY_ID_FORMAT,
    BinarySensorDeviceClass,
    BinarySensorEntity,
    BinarySensorEntityDescription,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import STATE_UNKNOWN, EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.util import slugify as util_slugify

from .base import VectorBase
from .const import DOMAIN, STATE_ROBOT_IS_CHARGNING, STATE_ROBOT_IS_ON_CHARGER
from .helpers.states import States

_LOGGER = logging.getLogger(__name__)


@dataclass
class VectorBinarySensorEntityDescription(BinarySensorEntityDescription):
    """Describes a Vector binary_sensor."""

    value_fn: Callable[[States]] | None = None


BINARY_SENSORS = [
    VectorBinarySensorEntityDescription(
        key="is_charging",
        device_class=BinarySensorDeviceClass.BATTERY_CHARGING,
        entity_category=EntityCategory.DIAGNOSTIC,
        name="Charging",
        value_fn=lambda states: (
            states.robot_battery_attributes(STATE_ROBOT_IS_CHARGNING)
            if not states.robot_battery_state() == STATE_UNKNOWN
            else STATE_UNKNOWN
        ),
    ),
    VectorBinarySensorEntityDescription(
        key="on_charger",
        device_class=None,
        entity_category=EntityCategory.DIAGNOSTIC,
        name="On charger",
        value_fn=lambda states: (
            states.robot_battery_attributes(STATE_ROBOT_IS_ON_CHARGER)
            if not states.robot_battery_state() == STATE_UNKNOWN
            else STATE_UNKNOWN
        ),
    ),
]


class VectorBaseBinarySensorEntity(VectorBase, BinarySensorEntity):
    """Define a Vector binary_sensor."""

    def __init__(
        self,
        description: VectorBinarySensorEntityDescription,
        coordinator,
    ):
        """Initialize a base sensor."""
        from .coordinator import (  # pylint: disable=import-outside-toplevel
            VectorDataUpdateCoordinator,
        )

        VectorBase.__init__(self, coordinator)

        self.entity_description = description

        self._attr_unique_id = util_slugify(
            f"{self.entry.unique_id}-button-{self.entity_description.name}"
        )

        self.entity_id = ENTITY_ID_FORMAT.format(
            util_slugify(
                f"{self.coordinator.vector_name}_{self.entity_description.name}"
            )
        )

        self._attr_icon = self.entity_description.icon

        self._attr_extra_state_attributes = {}
        self._attr_name = self.entity_description.name

        self._handle_coordinator_update()

    def _handle_coordinator_update(self):
        """Handle data update."""

        self._attr_is_on = self.entity_description.value_fn(self.coordinator.states)
        self.schedule_update_ha_state()


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Add Vector sensor entries."""
    coordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]

    sensor_entities = []
    for binary_sensor in BINARY_SENSORS:
        entity = VectorBaseBinarySensorEntity(binary_sensor, coordinator)
        _LOGGER.debug(
            "Adding binary_sensor '%s' with entity_id '%s'",
            binary_sensor.name,
            entity.entity_id,
        )
        sensor_entities.append(entity)

    async_add_entities(sensor_entities)
