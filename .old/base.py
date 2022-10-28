"""Base definitions."""
from __future__ import annotations

import logging
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import timedelta
from functools import partial

from ha_vector.exceptions import VectorAsyncException, VectorTimeoutException
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.event import async_call_later
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, STATE_FIRMWARE_VERSION, STATE_NO_DATA
from .coordinator import VectorConnectionState, VectorDataUpdateCoordinator
from .vector_utils.states_handler import VectorState

_LOGGER = logging.getLogger(__name__)


def connect(self) -> bool:
    """Open robot connection."""
    _LOGGER.debug("Connecting to Vector")
    try:
        self.connection_state = VectorConnectionState.CONNECTING
        self.robot.connect()
        self.connection_state = VectorConnectionState.CONNECTED

        return True
    except VectorAsyncException:
        _LOGGER.debug("Async exception, returning true anyway")
        self.connection_state = VectorConnectionState.CONNECTED
        return True
    except VectorTimeoutException:
        _LOGGER.warning("Timeout connecting to Vector, trying again later.")
        self.connection_state = VectorConnectionState.DISCONNECTED
        async_call_later(self.hass, timedelta(minutes=1), partial(self.connect))
        return False


@dataclass
class VectorBaseEntityDescription:
    """Describes a Vector sensor."""

    translate_key: str | None = None
    start_value: str = STATE_NO_DATA
    value_fn: Callable[[VectorState]] | str = start_value
    attribute_fn: Callable[[VectorState]] | str = field(default_factory=dict)


class VectorBase(CoordinatorEntity[VectorDataUpdateCoordinator]):
    """Defines a Vector base class."""

    _attr_icon = "mdi:robot"

    def __init__(
        self,
        hass: HomeAssistant,
        entry: ConfigEntry,
        coordinator: VectorDataUpdateCoordinator,
    ):
        """Initialise a Vector base."""
        # super().__init__(hass, entry)
        super().__init__(coordinator)
        self.hass = hass
        self.entry = entry
        self.coordinator = coordinator
        self._generation = "1.0" if self.coordinator.serial.startswith("00") else "2.0"
        self._vendor = "Anki" if self._generation == "1.0" else "Digital Dream Labs"

    @property
    def device_info(self) -> dict:
        """Set device information."""

        return {
            "identifiers": {
                (DOMAIN, self.entry.entry_id, self.coordinator.friendly_name)
            },
            "name": str(self.coordinator.friendly_name),
            "manufacturer": self._vendor,
            "model": "Vector",
            "sw_version": self.coordinator.states.get_robot_attributes(
                STATE_FIRMWARE_VERSION
            ),
            "hw_version": self._generation,
        }

    # async def async_added_to_hass(self) -> None:
    #     """When entity is added to hass."""
    #     self.coordinator.is_added = True
