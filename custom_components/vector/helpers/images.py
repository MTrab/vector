"""For handling images."""
from __future__ import annotations

import io


def convert_pil_image_to_byte_array(img):
    """Convert a PIL to bytes."""
    img_byte_array = io.BytesIO()
    img.save(img_byte_array, format="JPEG", subsampling=0, quality=100)
    img_byte_array = img_byte_array.getvalue()
    return img_byte_array
