"""Vector services handler."""
# pylint: disable=unused-argument
from __future__ import annotations
import asyncio

import logging
from functools import partial

from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.config_entries import ConfigEntry

from ..const import (
    ATTR_MESSAGE,
    ATTR_USE_VECTOR_VOICE,
    DOMAIN,
    SERVICE_GOTO_CHARGER,
    SERVICE_LEAVE_CHARGER,
    SERVICE_SPEAK,
)
from ..schemes import TTS

_LOGGER = logging.getLogger(__name__)


class VectorService:
    """Class for handling service calls to Vector."""

    def __init__(
        self,
        hass: HomeAssistant,
        entry: ConfigEntry,
        coordinator,
    ) -> None:
        """Initialize the service handler."""
        from ..coordinator import VectorDataUpdateCoordinator # pylint: disable=import-outside-toplevel

        self.coordinator:VectorDataUpdateCoordinator = coordinator
        self.entry = entry
        self.hass = hass
        self.speak = None

        # TTS / Speak
        self.hass.services.async_register(
            DOMAIN, SERVICE_SPEAK, partial(self.async_tts), schema=TTS
        )
        # Drive onto charger
        self.hass.services.async_register(
            DOMAIN, SERVICE_GOTO_CHARGER, partial(self.async_drive_on_charger)
        )
        # Drive off charger
        self.hass.services.async_register(
            DOMAIN, SERVICE_LEAVE_CHARGER, partial(self.async_drive_off_charger)
        )

    async def async_tts(self, service_call: ServiceCall) -> None:
        """Make Vector speak."""
        await self.speak.async_speak(
            text=service_call.data[ATTR_MESSAGE],
            use_vector_voice=service_call.data[ATTR_USE_VECTOR_VOICE],
            force_speech=True,
        )

    async def async_drive_on_charger(self, *args, **kwargs) -> None:
        """Send Vector to the charger."""
        await asyncio.wrap_future(self.coordinator.robot.conn.request_control())
        await asyncio.wrap_future(self.coordinator.robot.behavior.drive_on_charger())
        await asyncio.wrap_future(self.coordinator.robot.conn.release_control())

    async def async_drive_off_charger(self, *args, **kwargs) -> None:
        """Send Vector to the charger."""
        await asyncio.wrap_future(self.coordinator.robot.conn.request_control())
        await asyncio.wrap_future(self.coordinator.robot.behavior.drive_off_charger())
        await asyncio.wrap_future(self.coordinator.robot.conn.release_control())
