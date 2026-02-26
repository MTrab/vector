"""Constants for the Vector integration."""

from __future__ import annotations

DOMAIN = "vector"
PLATFORMS: list[str] = ["sensor", "select", "camera"]

CONF_HOST = "host"
CONF_ROBOT_NAME = "robot_name"
CONF_SERIAL = "serial"
CONF_EMAIL = "email"

VECTOR_NAME_PREFIX = "Vector-"

DEFAULT_SCAN_INTERVAL_SECONDS = 30

# Robot status flags from Vector protobuf (messages.proto -> RobotStatus)
ROBOT_STATUS_IS_ANIMATING = 0x40

# Status flags to ignore when deriving high-level activity.
EXCLUDED_ACTIVITY_STATUS_FLAGS: set[int] = {
    ROBOT_STATUS_IS_ANIMATING,
}

MASTER_VOLUME_OPTIONS: tuple[str, ...] = (
    "mute",
    "low",
    "medium_low",
    "medium",
    "medium_high",
    "high",
)
