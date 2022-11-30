"""Data mappings used for Vector robot integration."""
from __future__ import annotations

from .const import (
    ICON_CUBE,
    ICON_FACE,
    ICON_ROBOT,
    STATE_FULL,
    STATE_LOW,
    STATE_NO_DATA,
    STATE_NORMAL,
)

# Battery
BATTERYMAP_TO_STATE = {
    0: STATE_NO_DATA,
    1: STATE_LOW,
    2: STATE_NORMAL,
    3: STATE_FULL,
}

CUBE_BATTERYMAP_TO_STATE = {0: STATE_LOW, 1: STATE_NORMAL}

ICONS = {
    ICON_ROBOT: "mdi:robot",
    ICON_CUBE: "mdi:cube",
    ICON_FACE: "mdi:face-recognition",
}
