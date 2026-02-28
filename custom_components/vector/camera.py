"""Camera platform for Vector integration."""

from __future__ import annotations

from homeassistant.components.camera import Camera
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .assets import VectorAsset, VectorAssetHandler
from .coordinator import VectorCoordinator
from .entity import VectorEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Vector camera entities from config entry."""
    coordinator: VectorCoordinator = entry.runtime_data["coordinator"]
    async_add_entities(
        [
            VectorVisionCamera(coordinator, entry),
            VectorNavMapCamera(coordinator, entry),
        ]
    )


class VectorVisionCamera(VectorEntity, Camera):
    """Vector camera entity using robot CameraFeed stream."""

    _attr_has_entity_name = True
    _attr_translation_key = "vision"
    _attr_entity_registry_enabled_default = False
    _attr_frame_interval = 0.2

    def __init__(self, coordinator: VectorCoordinator, entry: ConfigEntry) -> None:
        """Initialize Vector camera entity."""
        Camera.__init__(self)
        VectorEntity.__init__(self, coordinator, entry)
        self._attr_unique_id = f"{entry.entry_id}_vision"
        self._assets = VectorAssetHandler()

    async def async_added_to_hass(self) -> None:
        """Prepare bundled fallback assets."""
        await super().async_added_to_hass()
        await self._assets.async_prepare(self.hass)

    async def async_camera_image(
        self,
        width: int | None = None,
        height: int | None = None,
    ) -> bytes | None:
        """Return latest camera frame bytes."""
        del width, height

        if self.coordinator.current_activity == "sleeping":
            return self._assets.image_bytes(VectorAsset.IMG_SLEEP)

        frame = await self.coordinator.async_get_latest_camera_frame(wait_timeout=1.0)
        if frame is not None:
            return frame

        return self._assets.image_bytes(VectorAsset.IMG_UNKNOWN)


class VectorNavMapCamera(VectorEntity, Camera):
    """Vector nav map camera entity using NavMapFeed stream."""

    _attr_has_entity_name = True
    _attr_translation_key = "nav_map"
    _attr_entity_registry_enabled_default = False
    _attr_frame_interval = 0.1

    def __init__(self, coordinator: VectorCoordinator, entry: ConfigEntry) -> None:
        """Initialize Vector nav map camera entity."""
        Camera.__init__(self)
        VectorEntity.__init__(self, coordinator, entry)
        self._attr_unique_id = f"{entry.entry_id}_nav_map"
        self.content_type = "image/png"
        self._unsub_nav_map_listener = None

    async def async_added_to_hass(self) -> None:
        """Register nav-map update listener for cache-busting token refresh."""
        await super().async_added_to_hass()

        @callback
        def _handle_nav_map_frame_update() -> None:
            self.async_update_token()
            self.async_write_ha_state()

        self._unsub_nav_map_listener = self.coordinator.async_add_nav_map_listener(
            _handle_nav_map_frame_update
        )

    async def async_will_remove_from_hass(self) -> None:
        """Unsubscribe nav-map listener."""
        if self._unsub_nav_map_listener is not None:
            self._unsub_nav_map_listener()
            self._unsub_nav_map_listener = None
        await super().async_will_remove_from_hass()

    async def async_camera_image(
        self,
        width: int | None = None,
        height: int | None = None,
    ) -> bytes | None:
        """Return latest nav map PNG frame bytes."""
        del width, height

        return await self.coordinator.async_get_latest_nav_map_frame(wait_timeout=None)
