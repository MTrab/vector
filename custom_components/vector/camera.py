"""Vector camera platform."""
from __future__ import annotations

import logging

from homeassistant.components.camera import ENTITY_ID_FORMAT, Camera,CameraEntityFeature
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.util import slugify as util_slugify

from .assets import VectorAsset, VectorAssetHandler
from .base import VectorBase
from .const import DOMAIN
from .helpers import convert_pil_image_to_byte_array

_LOGGER = logging.getLogger(__name__)


class VectorCamera(VectorBase, Camera):
    """A Vector robot camera platform."""

    def __init__(
        self,
        hass: HomeAssistant,
        entry: ConfigEntry,
        coordinator,
        enabled: bool = True,
    ) -> None:
        """Initialize the camera entity."""
        Camera.__init__(self)
        super().__init__(coordinator)

        self._enabled = enabled

        self._attr_name = f"{self.coordinator.vector_name} Vision"
        self.entity_id = ENTITY_ID_FORMAT.format(
            util_slugify(f"{self.coordinator.vector_name}_Vector_Vision")
            .replace("-", "_")
            .lower()
        )
        self._attr_unique_id = util_slugify(
            f"{self.coordinator.vector_name}_camera_vision"
        )
        self._attr_frame_interval=0.1
        self.assets = VectorAssetHandler()
        self._attr_supported_features = CameraEntityFeature.STREAM

    async def async_camera_image(
        self, width: int | None = None, height: int | None = None
    ) -> bytes | None:
        """Return the camera image."""

        if not self.coordinator.robot.camera.image_streaming_enabled():
            _LOGGER.debug(
                "Camera feed was not enabled for %s - enabling",
                self.coordinator.vector_name,
            )
            self.coordinator.robot.camera.init_camera_feed()

        if self.coordinator.states.robot_state == "sleeping":
            _LOGGER.debug(
                "%s is sleeping, let's show a sleep image", self.coordinator.vector_name
            )
            return self.assets.image_to_bytearray(VectorAsset.IMG_SLEEP)

        if self.coordinator.states.got_image:
            # return self.coordinator.states.last_image
            return convert_pil_image_to_byte_array(
                self.coordinator.robot.camera.latest_image.raw_image
            )

        _LOGGER.debug(
            "Haven't received any images for %s, showing a default image.",
            self.coordinator.vector_name,
        )
        return self.assets.image_to_bytearray(VectorAsset.IMG_UNKNOWN)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Vector camera entities setup."""
    coordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]

    entities = []
    constructor = VectorCamera(hass, entry, coordinator)
    entities.append(constructor)

    async_add_entities(entities, True)
