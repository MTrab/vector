"""Services definitions."""

from __future__ import annotations

import logging
from dataclasses import dataclass

import voluptuous as vol
from homeassistant.const import CONF_DEVICE_ID, CONF_ENTITY_ID
from homeassistant.core import HomeAssistant, ServiceCall, callback
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.device_registry import DeviceEntry
from homeassistant.helpers.service import async_extract_config_entry_ids

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

SERVICE_TTS = "tts"
SCHEMA_TTS = vol.Schema(
    {
        vol.Required("device_id"): str,
        vol.Required("message"): str,
        vol.Optional("use_vector_voice", default=True): bool,
    }
)


async def _async_tts(service_call: ServiceCall) -> None:
    """Tell Vector to speak this message."""
    hass = service_call.hass
    target_entry_ids = await async_extract_config_entry_ids(hass, service_call)
    target_entries: list = [
        loaded_entry
        for loaded_entry in hass.config_entries.async_loaded_entries(DOMAIN)
        if loaded_entry.entry_id in target_entry_ids
    ]
    _LOGGER.debug(target_entries)


async def async_setup_services(hass: HomeAssistant) -> None:
    """Set up services for the integration."""
    _LOGGER.debug("Registering services")
    hass.services.async_register(
        DOMAIN,
        SERVICE_TTS,
        _async_tts,
        SCHEMA_TTS,
    )
