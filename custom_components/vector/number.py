"""Number platform for Vector integration."""

from __future__ import annotations

from homeassistant.components.number import NumberEntity, NumberMode
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .coordinator import VectorCoordinator
from .entity import VectorEntity

_DEFAULT_CUSTOM_HUE = 0.5
_DEFAULT_CUSTOM_SATURATION = 1.0


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Vector numbers from a config entry."""
    coordinator: VectorCoordinator = entry.runtime_data["coordinator"]
    async_add_entities(
        [
            VectorCustomEyeColorHueNumber(coordinator, entry),
            VectorCustomEyeColorSaturationNumber(coordinator, entry),
        ]
    )


class VectorCustomEyeColorHueNumber(VectorEntity, NumberEntity):
    """Custom eye color hue number entity."""

    _attr_has_entity_name = True
    _attr_translation_key = "custom_eye_color_hue"
    _attr_entity_category = EntityCategory.CONFIG
    _attr_mode = NumberMode.SLIDER
    _attr_native_min_value = 0.0
    _attr_native_max_value = 1.0
    _attr_native_step = 0.01
    _attr_entity_registry_enabled_default = False

    def __init__(self, coordinator: VectorCoordinator, entry: ConfigEntry) -> None:
        """Initialize custom eye color hue number."""
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{entry.entry_id}_custom_eye_color_hue"

    @property
    def native_value(self) -> float | None:
        """Return current custom eye color hue."""
        return self.coordinator.eye_color_custom_hue

    async def async_set_native_value(self, value: float) -> None:
        """Set custom eye color hue and preserve saturation."""
        saturation = (
            self.coordinator.eye_color_custom_saturation
            if self.coordinator.eye_color_custom_saturation is not None
            else _DEFAULT_CUSTOM_SATURATION
        )
        await self.coordinator.async_set_custom_eye_color(
            hue=float(value),
            saturation=float(saturation),
        )


class VectorCustomEyeColorSaturationNumber(VectorEntity, NumberEntity):
    """Custom eye color saturation number entity."""

    _attr_has_entity_name = True
    _attr_translation_key = "custom_eye_color_saturation"
    _attr_entity_category = EntityCategory.CONFIG
    _attr_mode = NumberMode.SLIDER
    _attr_native_min_value = 0.0
    _attr_native_max_value = 1.0
    _attr_native_step = 0.01
    _attr_entity_registry_enabled_default = False

    def __init__(self, coordinator: VectorCoordinator, entry: ConfigEntry) -> None:
        """Initialize custom eye color saturation number."""
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{entry.entry_id}_custom_eye_color_saturation"

    @property
    def native_value(self) -> float | None:
        """Return current custom eye color saturation."""
        return self.coordinator.eye_color_custom_saturation

    async def async_set_native_value(self, value: float) -> None:
        """Set custom eye color saturation and preserve hue."""
        hue = (
            self.coordinator.eye_color_custom_hue
            if self.coordinator.eye_color_custom_hue is not None
            else _DEFAULT_CUSTOM_HUE
        )
        await self.coordinator.async_set_custom_eye_color(
            hue=float(hue),
            saturation=float(value),
        )
