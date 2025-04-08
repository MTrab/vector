"""Add support for buttons to the device."""

from __future__ import annotations

import logging
from collections.abc import Callable
from dataclasses import dataclass

from homeassistant.components.button import (
    ENTITY_ID_FORMAT,
    ButtonDeviceClass,
    ButtonEntity,
    ButtonEntityDescription,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.util import slugify as util_slugify

from .base import VectorBase
from .const import DOMAIN, STATE_ROBOT_IS_ON_CHARGER
from .coordinator import VectorDataUpdateCoordinator
from .helpers.states import States

_LOGGER = logging.getLogger(__name__)


@dataclass
class VectorButtonEntityDescription(ButtonEntityDescription):
    """Describes a Vector button."""

    command_fn: Callable[[VectorDataUpdateCoordinator]] | None = None
    available_fn: Callable[[States]] | None = None


BUTTONS = [
    VectorButtonEntityDescription(
        key="leave_charger",
        device_class=None,
        entity_category=None,
        name="Leave charger",
        command_fn=lambda conn: conn.leave_charger(),
        available_fn=lambda states: states.robot_battery_attributes(
            STATE_ROBOT_IS_ON_CHARGER
        )
        == True,
    ),
    VectorButtonEntityDescription(
        key="dock_charger",
        device_class=None,
        entity_category=None,
        name="Go to charger",
        command_fn=lambda conn: conn.dock_charger(),
        available_fn=lambda states: states.robot_battery_attributes(
            STATE_ROBOT_IS_ON_CHARGER
        )
        == False,
    ),
]


class VectorBaseButtonEntity(VectorBase, ButtonEntity):
    """Define a Vector button."""

    def __init__(
        self,
        description: VectorButtonEntityDescription,
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

    async def _async_press_action(self) -> None:
        """Press the button."""
        _LOGGER.debug("Button '%s' was pressed", self.name)
        await self.entity_description.command_fn(self.coordinator)

    @property
    def available(self) -> bool:
        """Set availability."""
        if not isinstance(self.entity_description.available_fn, type(None)):
            return self.entity_description.available_fn(self.coordinator.states)


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Add Vector button entries."""
    coordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]

    entities = []
    for button in BUTTONS:
        entity = VectorBaseButtonEntity(button, coordinator)
        _LOGGER.debug(
            "Adding button '%s' with entity_id '%s'", button.name, entity.entity_id
        )
        entities.append(entity)

    async_add_entities(entities)
