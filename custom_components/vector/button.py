"""Button platform for Vector integration."""

from __future__ import annotations

from homeassistant.components.button import ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .coordinator import VectorCoordinator
from .entity import VectorEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Vector buttons from a config entry."""
    coordinator: VectorCoordinator = entry.runtime_data["coordinator"]
    async_add_entities(
        [
            VectorSleepButton(coordinator, entry),
            VectorGoHomeButton(coordinator, entry),
            VectorExploreStartButton(coordinator, entry),
            VectorDanceButton(coordinator, entry),
            VectorFetchCubeButton(coordinator, entry),
        ]
    )


class _VectorQuickActionButton(VectorEntity, ButtonEntity):
    """Base class for Vector quick-action buttons."""

    _action_key: str

    async def async_press(self) -> None:
        """Trigger quick action on button press."""
        await self.coordinator.async_trigger_quick_action(self._action_key)


class VectorSleepButton(_VectorQuickActionButton):
    """Button for sending Vector to sleep."""

    _attr_has_entity_name = True
    _attr_translation_key = "sleep"
    _attr_icon = "mdi:sleep"
    _action_key = "sleep"

    def __init__(self, coordinator: VectorCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{entry.entry_id}_quick_action_sleep"


class VectorGoHomeButton(_VectorQuickActionButton):
    """Button for sending Vector to charger."""

    _attr_has_entity_name = True
    _attr_translation_key = "go_home"
    _attr_icon = "mdi:home-import-outline"
    _action_key = "go_home"

    def __init__(self, coordinator: VectorCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{entry.entry_id}_quick_action_go_home"


class VectorExploreStartButton(_VectorQuickActionButton):
    """Button for starting Vector explore behavior."""

    _attr_has_entity_name = True
    _attr_translation_key = "explore_start"
    _attr_icon = "mdi:compass-outline"
    _action_key = "explore_start"

    def __init__(self, coordinator: VectorCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{entry.entry_id}_quick_action_explore_start"


class VectorDanceButton(_VectorQuickActionButton):
    """Button for starting Vector dance behavior."""

    _attr_has_entity_name = True
    _attr_translation_key = "dance"
    _attr_icon = "mdi:music-circle-outline"
    _action_key = "dance"

    def __init__(self, coordinator: VectorCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{entry.entry_id}_quick_action_dance"


class VectorFetchCubeButton(_VectorQuickActionButton):
    """Button for starting Vector fetch-cube behavior."""

    _attr_has_entity_name = True
    _attr_translation_key = "fetch_cube"
    _attr_icon = "mdi:cube-outline"
    _action_key = "fetch_cube"

    def __init__(self, coordinator: VectorCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{entry.entry_id}_quick_action_fetch_cube"
