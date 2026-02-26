"""Static image assets for Vector entities."""

from __future__ import annotations

from enum import Enum
from pathlib import Path


class VectorAsset(Enum):
    """Supported bundled asset files."""

    IMG_SLEEP = "vector_sleep.png"
    IMG_UNKNOWN = "vector_unknown.png"


class VectorAssetHandler:
    """Load and cache bundled image assets."""

    def __init__(self) -> None:
        self._base_path = Path(__file__).resolve().parent
        self._cache: dict[VectorAsset, bytes] = {}

    def image_bytes(self, asset: VectorAsset) -> bytes:
        cached = self._cache.get(asset)
        if cached is not None:
            return cached

        data = (self._base_path / asset.value).read_bytes()
        self._cache[asset] = data
        return data
