"""Vector robot integration."""
from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_EMAIL, CONF_NAME, CONF_PASSWORD
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.loader import async_get_integration
from homeassistant.util import slugify as util_slugify

from .coordinator import VectorDataSetUpdateCoordinator, VectorDataUpdateCoordinator

from .const import BANNER, DOMAIN
from .helpers import VectorStore

_LOGGER = logging.getLogger(__name__)

VALID_PLATFORMS = ["sensor"]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up cloud API connector from a config entry."""
    integration = await async_get_integration(hass, DOMAIN)
    _LOGGER.info(BANNER, integration.version)

    if not DOMAIN in hass.data:
        hass.data.setdefault(DOMAIN, {})
        # Initialize datasets for random speech (Jokes, Facts ...)
        dataset_coordinator = VectorDataSetUpdateCoordinator(hass)
        await dataset_coordinator.async_config_entry_first_refresh()
        hass.data[DOMAIN]["datasets"] = dataset_coordinator

    store = VectorStore(hass, entry.data[CONF_NAME])
    await store.async_load()

    hass.data[DOMAIN][entry.entry_id] = {
        "coordinator": None,
        "config": store,
    }

    try:
        coordinator = VectorDataUpdateCoordinator(hass, entry)
    except HomeAssistantError as exc:
        _LOGGER.error("%s - you could try rebooting the robot", exc)
        return False

    hass.data[DOMAIN][entry.entry_id]["coordinator"] = coordinator

    await coordinator.async_config_entry_first_refresh()

    hass.config_entries.async_setup_platforms(entry, VALID_PLATFORMS)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, VALID_PLATFORMS)

    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)

        return True

    return False


async def async_reload_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload config entry."""
    await async_unload_entry(hass, entry)
    await async_setup_entry(hass, entry)
