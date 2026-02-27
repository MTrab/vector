"""The Vector integration."""

from __future__ import annotations

import asyncio
from typing import TypedDict

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady

from .const import PLATFORMS
from .coordinator import VectorCoordinator

_SETUP_VALIDATION_TIMEOUT_SECONDS = 20.0


class VectorRuntimeData(TypedDict):
    """Runtime data stored on config entries."""

    coordinator: VectorCoordinator
    start_task: asyncio.Task[None] | None


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Vector from a config entry."""
    coordinator = VectorCoordinator(hass, entry)

    try:
        await asyncio.wait_for(
            coordinator.async_validate_connection(),
            timeout=_SETUP_VALIDATION_TIMEOUT_SECONDS,
        )
    except TimeoutError as err:
        await coordinator.async_shutdown()
        raise ConfigEntryNotReady(
            f"Timed out validating Vector connection after {_SETUP_VALIDATION_TIMEOUT_SECONDS:.0f}s"
        ) from err
    except Exception as err:
        await coordinator.async_shutdown()
        raise ConfigEntryNotReady(
            f"Failed to validate Vector connection: {err}"
        ) from err

    entry.runtime_data = {
        "coordinator": coordinator,
        "start_task": None,
    }
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    start_task = hass.async_create_background_task(
        coordinator.async_start_runtime(),
        name=f"vector_start_{entry.entry_id}",
    )
    entry.runtime_data["start_task"] = start_task
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        runtime_data: VectorRuntimeData | None = entry.runtime_data
        if runtime_data:
            start_task = runtime_data.get("start_task")
            if start_task is not None:
                start_task.cancel()
            coordinator = runtime_data.get("coordinator")
            if coordinator is not None:
                await coordinator.async_shutdown()
            entry.runtime_data = None
    return unload_ok
