"""Vector robot cameras."""
# pylint: disable=unused-argument
from __future__ import annotations

import logging
from dataclasses import dataclass
from enum import IntEnum

from homeassistant.components.camera import (
    ENTITY_ID_FORMAT,
    Camera,
    CameraEntityDescription,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import STATE_UNAVAILABLE
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.util import slugify as util_slugify

from .assets import VectorAsset, VectorAssetHandler
from .base import VectorBase
from .const import DOMAIN
from .coordinator import VectorDataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)


class VectorCameraFeature(IntEnum):
    """Different camera types."""

    MAIN_CAM = 0
    NAV_MAP = 1


@dataclass
class VectorCameraDescription(CameraEntityDescription):
    """Extending camera description for Vector use."""

    image_attribute: str = None


CAMERAS = [
    VectorCameraDescription(
        key=VectorCameraFeature.MAIN_CAM, name="Vision", image_attribute="last_image"
    ),
    # VectorCameraDescription(
    #     key=VectorCameraFeature.NAV_MAP,
    #     name="Navigation Map",
    #     image_attribute="navigation_map",
    # ),
]


class VectorCamera(VectorBase, Camera):
    """A Vector robot camera."""

    entity_description: CameraEntityDescription

    def __init__(
        self,
        hass: HomeAssistant,
        entry: ConfigEntry,
        description: CameraEntityDescription,
        coordinator: VectorDataUpdateCoordinator,
        enabled: bool = True,
    ) -> None:
        """Initialize a Vector camera entity."""
        Camera.__init__(self)
        super().__init__(hass, entry, coordinator)
        self._assets = VectorAssetHandler()
        self._old_state = ""
        self._enabled = enabled
        self.entity_description = description
        self._attr_name = self.entity_description.name
        self.entity_id = ENTITY_ID_FORMAT.format(
            util_slugify(f"{self.coordinator.vector_name}_{description.name}")
            .replace("-", "_")
            .lower()
        )
        self._attr_unique_id = util_slugify(
            f"{self.coordinator.vector_name}_camera_{description.key}"
        )

    async def async_camera_image(
        self, width: int | None = None, height: int | None = None
    ) -> bytes | None:
        """Return the camera image."""
        state = self.coordinator.states.robot_state

        if not self.coordinator.robot.camera.image_streaming_enabled():
            _LOGGER.debug("Enabling camera feed")
            self.coordinator.robot.camera.init_camera_feed()

        if state == "sleeping":
            _LOGGER.debug(
                "%s is sleeping, let's show a sleep image", self.coordinator.vector_name
            )
            return self._assets.image_to_bytearray(VectorAsset.IMG_SLEEP)

        if state in ["no_data", STATE_UNAVAILABLE] or isinstance(
            getattr(self.coordinator.states, self.entity_description.image_attribute),
            type(None),
        ):
            _LOGGER.debug(
                "No knowledge of what %s is doing or no image received (%s, %s), "
                "let's show the default image",
                self.coordinator.vector_name,
                state,
                isinstance(
                    getattr(
                        self.coordinator.states, self.entity_description.image_attribute
                    ),
                    type(None),
                ),
            )
            return self._assets.image_to_bytearray(VectorAsset.IMG_UNKNOWN)
        elif self.coordinator.states.got_image:
            return getattr(
                self.coordinator.states, self.entity_description.image_attribute
            )
        else:
            _LOGGER.debug(
                "No matching states for %s, showing unknown image.",
                self.coordinator.vector_name,
            )
            return self._assets.image_to_bytearray(VectorAsset.IMG_UNKNOWN)

    # async def stream_source(self) -> str | None:
    #     """Return the stream source."""


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Vector camera entities setup."""
    coordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]

    entities = []
    for camera in CAMERAS:
        constructor = VectorCamera(hass, entry, camera, coordinator)

        entities.append(constructor)

    async_add_entities(entities, True)
