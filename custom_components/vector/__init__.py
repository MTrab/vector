"""Vector robot integration."""

from __future__ import annotations

import logging
from typing import Optional, cast

import grpc
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_EMAIL, CONF_NAME, CONF_PASSWORD
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady, HomeAssistantError
from homeassistant.loader import async_get_integration
from homeassistant.util import slugify as util_slugify

from .const import BANNER, DOMAIN
from .coordinator import VectorDataSetUpdateCoordinator, VectorDataUpdateCoordinator
from .helpers import VectorEvents, VectorStore
from .helpers.cubes import Cubes
from .helpers.speech import Speech
from .services import async_setup_services

_LOGGER = logging.getLogger(__name__)

VALID_PLATFORMS = ["binary_sensor", "button", "sensor"]  # , "camera"]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up cloud API connector from a config entry."""
    integration = await async_get_integration(hass, DOMAIN)
    _LOGGER.info(BANNER, integration.version)

    if not DOMAIN in hass.data:
        hass.data.setdefault(DOMAIN, {})

    if not "datasets" in hass.data[DOMAIN]:
        # Initialize datasets for random speech (Jokes, Facts ...)
        _LOGGER.debug("Initializing datasets for chatter")
        dataset_coordinator = VectorDataSetUpdateCoordinator(hass)
        await dataset_coordinator.async_config_entry_first_refresh()
        hass.data[DOMAIN]["datasets"] = dataset_coordinator
    else:
        dataset_coordinator = hass.data[DOMAIN]["datasets"]

    store = VectorStore(hass, entry.data[CONF_NAME])
    config = cast(Optional[dict], await store.async_load())

    _LOGGER.debug("Config: %s", config)
    hass.data[DOMAIN][entry.entry_id] = {
        "coordinator": None,
        "config": config,
        "events": None,
        "speech": None,
    }

    if not "cubes" in hass.data[DOMAIN]:
        hass.data[DOMAIN]["cubes"] = Cubes(hass, entry.entry_id)

    try:
        coordinator = VectorDataUpdateCoordinator(hass, entry)
        await coordinator.connect()
    except HomeAssistantError as exc:
        raise ConfigEntryNotReady(
            f"Error connecting to {entry.data[CONF_NAME]}: {exc}"
        ) from exc

    hass.data[DOMAIN][entry.entry_id]["coordinator"] = coordinator
    hass.data[DOMAIN][entry.entry_id]["events"] = VectorEvents(hass, entry, coordinator)
    hass.data[DOMAIN][entry.entry_id]["speech"] = Speech(
        hass, dataset_coordinator._datasets.path, coordinator.robot
    )

    await coordinator.async_subscribe_events()
    await coordinator.async_config_entry_first_refresh()

    await hass.config_entries.async_forward_entry_setups(entry, VALID_PLATFORMS)

    await async_setup_services(hass)

    coordinator.first_run = False
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
