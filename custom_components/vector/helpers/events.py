"""Handle events from Vector."""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from ha_vector.events import Events
from ha_vector import Robot

_LOGGER = logging.getLogger(__name__)

EVENTS = {
    Events.new_raw_camera_image: "on_image",
    Events.robot_state: "on_robot_state",
    Events.time_stamped_status: "on_time_stamped_status",
}


class VectorEvents:
    """Class for handling event subscriptions and dataflow."""

    def __init__(
        self,
        hass: HomeAssistant,
        entry: ConfigEntry,
        coordinator,
    ) -> None:
        """Initialize the event handlers."""
        self.coordinator = coordinator
        self.entry = entry
        self.hass = hass

    async def async_subscribe(self, event: Events = None, func: Any = None) -> None:
        """Subscribe to specific event."""
        if isinstance(event, type(None)):
            for event, func in EVENTS.items():
                await self.async_subscribe(event, getattr(self, func))
        else:
            self.coordinator.robot.events.subscribe(func, event)

    async def on_robot_state(self, robot: Robot, event_type, event, *args, **kwargs):
        """Robot state received."""
        # _LOGGER.debug(event)

    def on_image(self, robot: Robot, event_type, event, *args, **kwargs):
        """Called when Vector receives a new image."""
        self.coordinator.states.got_image = True
        # self.coordinator.states.last_image = event.image.raw_image
        # self.coordinator.states.last_image = self.coordinator.robot.camera.raw_image

    async def on_time_stamped_status(
        self, robot: Robot, event_type, event, *args, **kwargs
    ):
        """Handle time stamped events (robot state)."""
        if event.status.feature_status.feature_name:
            feature = str(event.status.feature_status.feature_name)
            if feature.lower() != "nofeature":
                _LOGGER.debug("Feature reported: %s", feature)
                self.coordinator.states.set_robot_state(feature.lower())
