"""Vector robot buttons."""
from __future__ import annotations

import logging
from dataclasses import dataclass

from homeassistant.backports.enum import StrEnum
from homeassistant.components.button import (
    ENTITY_ID_FORMAT,
    ButtonEntity,
    ButtonEntityDescription,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.util import slugify as util_slugify

from .base import VectorBase, VectorBaseEntityDescription
from .const import BUTTON_GENERIC, DOMAIN, SERVICE_GOTO_CHARGER, SERVICE_LEAVE_CHARGER

_LOGGER = logging.getLogger(__name__)


class VectorButtonTypes(StrEnum):
    """Vector button types."""

    LEAVE_CHARGER = SERVICE_LEAVE_CHARGER
    GOTO_CHARGER = SERVICE_GOTO_CHARGER
    GENERIC = BUTTON_GENERIC


@dataclass
class VectorButtonEntityDescription(
    VectorBaseEntityDescription, ButtonEntityDescription
):
    """Describes a Vector button."""

    call_function: str | None = None
    call_param: dict | None = None


BUTTONS = [
    VectorButtonEntityDescription(
        key=VectorButtonTypes.LEAVE_CHARGER,
        name="Leave the charger",
        icon="mdi:home-export-outline",
        call_function="async_drive_off_charger",
    ),
    VectorButtonEntityDescription(
        key=VectorButtonTypes.GOTO_CHARGER,
        name="Go to the charger",
        icon="mdi:home-lightning-bolt",
        call_function="async_drive_on_charger",
    ),
    VectorButtonEntityDescription(
        key=VectorButtonTypes.GENERIC,
        name="Tell me a joke",
        icon="mdi:account-voice",
        call_function="async_speak_joke",
    ),
]


class VectorButton(VectorBase, ButtonEntity):
    """Defines a base Vector button."""

    entity_description: VectorButtonEntityDescription

    def __init__(
        self,
        hass: HomeAssistant,
        entry: ConfigEntry,
        description: VectorButtonEntityDescription,
        coordinator,
        service,
    ):
        super().__init__(hass, entry, coordinator)
        self.services = service
        self.entity_description = description
        self._call_function = description.call_function
        self.entity_id = ENTITY_ID_FORMAT.format(
            util_slugify(f"{self.coordinator.vector_name}_{description.key}")
        )
        self._attr_unique_id = util_slugify(
            f"{entry.unique_id}-button-{self.entity_description.name}"
        )
        self._attr_icon = description.icon

    async def async_press(self) -> None:
        """Handles button press."""
        call = getattr(self.services, self._call_function)
        await call()


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Create Vector buttons."""
    coordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]
    services = hass.data[DOMAIN][entry.entry_id]["services"]
    entities = []
    for button in BUTTONS:
        entities.append(VectorButton(hass, entry, button, coordinator, services))

    async_add_entities(entities, True)
