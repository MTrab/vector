"""Assets for use with Vector."""

from enum import Enum
import os


class VectorAsset(Enum):
    """Vector assets."""

    IMG_SLEEP = "vector_sleep.png"
    IMG_UNKNOWN = "vector_unknown.png"


CLS_TO_IMG = {}


class VectorAssetHandler:
    """Vector asset handler."""

    def __init__(self) -> None:
        """Initialize the handler."""
        self.path = os.path.dirname(os.path.abspath(__file__))

        for asset in VectorAsset:
            self.__preload(asset)

    def __preload(self, asset: VectorAsset) -> None:
        """Preload assets."""
        with open(os.path.join(self.path, asset.value), "rb") as img_obj:
            file = img_obj.read()
            CLS_TO_IMG.update({asset.name: bytearray(file)})

    def image_to_bytearray(self, asset: VectorAsset) -> bytearray:
        """Return an image as a bytearray."""
        return CLS_TO_IMG[asset.name] if asset.name in CLS_TO_IMG else bytearray()
