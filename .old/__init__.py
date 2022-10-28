"""Base definition of DDL Vector."""
# pylint: disable=unused-argument,protected-access
from __future__ import annotations

import logging
from datetime import timedelta
from typing import Optional, cast

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_EMAIL, CONF_NAME, CONF_PASSWORD
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady, HomeAssistantError
from homeassistant.loader import async_get_integration
from homeassistant.util import slugify as util_slugify

from .const import CONF_IP, CONF_SERIAL, DOMAIN, PLATFORMS, STARTUP
from .coordinator import VectorDataUpdateCoordinator
from .helpers.storage import VectorStore
# from .vector_utils.config import validate_input
from .vector_utils.datasetmanager import DataRunner
from .vector_utils.event_handler import VectorEvent
from .vector_utils.service_handler import VectorService

_LOGGER = logging.getLogger(__name__)

SCAN_INTERVAL = timedelta(minutes=1)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up cloud API connector from a config entry."""
    integration = await async_get_integration(hass, DOMAIN)
    _LOGGER.info(STARTUP, integration.version)

    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = {
        "coordinator": None,
        "events": None,
        "services": None,
        "speech": None,
        "listener": None,
        "datastore": None,
    }

    store = VectorStore(hass, entry.data[CONF_NAME])
    config = cast(Optional[dict], await store.async_load())

    dataset = DataRunner(hass, store.dataset_path)
    try:
        await dataset.async_refresh()
    except:  # pylint: disable=bare-except
        raise HomeAssistantError("Error fetching speech datasets for Vector") from None

    hass.data[DOMAIN][entry.entry_id]["config"] = config
    hass.data[DOMAIN][entry.entry_id]["datastore"] = store

    # try:
    coordinator = VectorDataUpdateCoordinator(hass, entry)
    # except VectorUnauthenticatedException:
    #     _LOGGER.warning(
    #         "Vector authentication token was invalidated, trying to generate new."
    #     )
    #     await validate_input(hass, entry.data)
    #     try:
    #         config = cast(Optional[dict], await store.async_load())
    #         hass.data[DOMAIN][entry.entry_id]["config"] = config
    #         coordinator = VectorDataUpdateCoordinator(hass, entry)
    #     except VectorUnauthenticatedException:
    #         raise HomeAssistantError(
    #             f"Couldn't setup a connection to {entry.data[CONF_NAME]} - "
    #             "try removing and add the integration again"
    #         ) from None
    # except Exception:  # pylint: disable=broad-except
    #     raise ConfigEntryNotReady(
    #         f"Couldn't setup a connection to {entry.data[CONF_NAME]} - try rebooting the robot"
    #     ) from None

    hass.data[DOMAIN][entry.entry_id]["coordinator"] = coordinator
    hass.data[DOMAIN][entry.entry_id]["events"] = VectorEvent(hass, entry, coordinator)
    hass.data[DOMAIN][entry.entry_id]["services"] = VectorService(
        hass, entry, coordinator
    )

    await check_unique_id(hass, entry)
    await coordinator.async_subscribe_events()
    try:
        await coordinator.async_config_entry_first_refresh()
    except ConfigEntryNotReady:
        # _LOGGER.debug(exc.with_traceback())
        raise ConfigEntryNotReady(
            f"Couldn't setup a connection to {entry.data[CONF_NAME]} for initial data update "
            "- try rebooting the robot"
        ) from None
    except:
        raise HomeAssistantError(
            f"Something went horrible wrong, communicating with {entry.data[CONF_NAME]}"
        ) from None

    hass.config_entries.async_setup_platforms(entry, PLATFORMS)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)

    coordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]
    # await coordinator.async_unsubscribe_events()

    try:
        # await hass.async_add_executor_job(coordinator.robot.disconnect)
        await coordinator.async_disconnect()
    except:  # pylint: disable=bare-except
        pass

    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)

        return True

    return False


async def async_reload_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload config entry."""
    await async_unload_entry(hass, entry)
    await async_setup_entry(hass, entry)


async def check_unique_id(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Check if a device unique ID is set."""
    _LOGGER.debug("Unique ID: %s", entry.unique_id)
    if not isinstance(entry.unique_id, type(None)):
        return

    new_unique_id = util_slugify(
        f"{entry.data.get(CONF_NAME)}_{entry.data.get(CONF_SERIAL)}"
    )

    _LOGGER.debug("Setting new unique ID %s", new_unique_id)
    data = {
        CONF_EMAIL: entry.data[CONF_EMAIL],
        CONF_PASSWORD: entry.data[CONF_PASSWORD],
        CONF_NAME: entry.data[CONF_NAME],
        CONF_IP: entry.data[CONF_IP],
        CONF_SERIAL: entry.data[CONF_SERIAL],
    }
    result = hass.config_entries.async_update_entry(
        entry, data=data, unique_id=new_unique_id
    )
    _LOGGER.debug("Update successful? %s", result)
