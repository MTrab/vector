"""The Vector integration."""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import DOMAIN, PLATFORMS
from .coordinator import VectorCoordinator


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Vector from a config entry."""
    hass.data.setdefault(DOMAIN, {})
    coordinator = VectorCoordinator(hass, entry)

    hass.data[DOMAIN][entry.entry_id] = {
        "config": dict(entry.data),
        "coordinator": coordinator,
        "start_task": None,
    }
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    start_task = hass.async_create_background_task(
        coordinator.async_start_runtime(),
        name=f"vector_start_{entry.entry_id}",
    )
    hass.data[DOMAIN][entry.entry_id]["start_task"] = start_task
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok and DOMAIN in hass.data:
        entry_data = hass.data[DOMAIN].pop(entry.entry_id, None)
        if entry_data:
            start_task = entry_data.get("start_task")
            if start_task is not None:
                start_task.cancel()
            coordinator: VectorCoordinator | None = entry_data.get("coordinator")
            if coordinator is not None:
                await coordinator.async_shutdown()
    return unload_ok
