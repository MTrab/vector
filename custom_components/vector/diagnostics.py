"""Diagnostics support for the Vector integration."""

from __future__ import annotations

from typing import Any

from homeassistant.components.diagnostics import async_redact_data
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, CONF_PASSWORD
from homeassistant.core import HomeAssistant

from .const import CONF_EMAIL, CONF_SERIAL, DOMAIN
from .coordinator import VectorCoordinator

TO_REDACT = {
    CONF_EMAIL,
    CONF_HOST,
    CONF_PASSWORD,
    CONF_SERIAL,
}


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: ConfigEntry
) -> dict[str, Any]:
    """Return diagnostics for a config entry."""
    entry_data = hass.data[DOMAIN][entry.entry_id]
    coordinator: VectorCoordinator = entry_data["coordinator"]

    return {
        "entry": async_redact_data(dict(entry.data), TO_REDACT),
        "coordinator": {
            "current_activity": coordinator.current_activity,
            "battery_percent": coordinator.battery_percent,
            "battery_level": coordinator.battery_level,
            "is_charging": coordinator.is_charging,
            "firmware_version": coordinator.firmware_version,
            "master_volume": coordinator.master_volume,
            "stimulation_value": coordinator.stimulation_value,
        },
    }
