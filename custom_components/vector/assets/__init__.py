"""Static image assets for Vector entities."""

from __future__ import annotations

from enum import Enum
from pathlib import Path

from homeassistant.core import HomeAssistant


class VectorAsset(Enum):
    """Supported bundled asset files."""

    IMG_SLEEP = "vector_sleep.png"
    IMG_UNKNOWN = "vector_unknown.png"


class VectorAssetHandler:
    """Load and cache bundled image assets."""

    def __init__(self) -> None:
        self._base_path = Path(__file__).resolve().parent
        self._cache: dict[VectorAsset, bytes] = {}

    async def async_prepare(self, hass: HomeAssistant) -> None:
        """Preload all known assets outside the event loop."""
        await hass.async_add_executor_job(self._preload_all)

    def _preload_all(self) -> None:
        for asset in VectorAsset:
            self._cache.setdefault(asset, self._read_asset(asset))

    def _read_asset(self, asset: VectorAsset) -> bytes:
        return (self._base_path / asset.value).read_bytes()

    def image_bytes(self, asset: VectorAsset) -> bytes:
        cached = self._cache.get(asset)
        if cached is not None:
            return cached

        data = self._read_asset(asset)
        self._cache[asset] = data
        return data
