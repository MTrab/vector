"""Data mappings used for Vector robot integration."""
from __future__ import annotations

from homeassistant.const import STATE_UNKNOWN

from .const import (
    ICON_CUBE,
    ICON_DISTANCE,
    ICON_FACE,
    ICON_ROBOT,
    ICON_STATS,
    STATE_FULL,
    STATE_LOW,
    STATE_NORMAL,
)

# Battery
BATTERYMAP_TO_STATE = {
    0: STATE_UNKNOWN,
    1: STATE_LOW,
    2: STATE_NORMAL,
    3: STATE_FULL,
}

CUBE_BATTERYMAP_TO_STATE = {0: STATE_LOW, 1: STATE_NORMAL}

ICONS = {
    ICON_ROBOT: "mdi:robot",
    ICON_CUBE: "mdi:cube",
    ICON_FACE: "mdi:face-recognition",
    ICON_STATS: "mdi:chart-gantt",
    ICON_DISTANCE: "mdi:map-marker-distance",
}
