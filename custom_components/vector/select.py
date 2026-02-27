"""Select platform for Vector integration."""

from __future__ import annotations

from homeassistant.components.select import SelectEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import MASTER_VOLUME_OPTIONS
from .coordinator import VectorCoordinator
from .entity import VectorEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Vector selects from a config entry."""
    coordinator: VectorCoordinator = entry.runtime_data["coordinator"]
    async_add_entities([VectorMasterVolumeSelect(coordinator, entry)])


class VectorMasterVolumeSelect(VectorEntity, SelectEntity):
    """Master volume select for Vector."""

    _attr_has_entity_name = True
    _attr_translation_key = "master_volume"
    _attr_entity_category = EntityCategory.CONFIG
    _attr_entity_registry_enabled_default = False

    def __init__(self, coordinator: VectorCoordinator, entry: ConfigEntry) -> None:
        """Initialize master volume select."""
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{entry.entry_id}_master_volume"
        self._attr_options = list(MASTER_VOLUME_OPTIONS)

    @property
    def current_option(self) -> str | None:
        """Return selected volume key."""
        return self.coordinator.master_volume

    async def async_select_option(self, option: str) -> None:
        """Set a new master volume option."""
        await self.coordinator.async_set_master_volume(option)
