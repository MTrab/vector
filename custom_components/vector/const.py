"""Constants for the Vector integration."""

from __future__ import annotations

from homeassistant.const import ATTR_ENTITY_ID, Platform

DOMAIN = "vector"
PLATFORMS: list[Platform] = [
    Platform.SENSOR,
    Platform.SELECT,
    Platform.BUTTON,
    Platform.CAMERA,
]

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

QUICK_ACTION_INTENTS: dict[str, str] = {
    "sleep": "intent_system_sleep",
    "go_home": "intent_system_charger",
    "explore_start": "explore_start",
    "dance": "intent_imperative_dance",
    "fetch_cube": "intent_imperative_fetchcube",
}

SERVICE_SAY_TEXT = "say_text"
ATTR_ENTRY_ID = "entry_id"
ATTR_TEXT = "text"
ATTR_USE_VECTOR_VOICE = "use_vector_voice"
ATTR_DURATION_SCALAR = "duration_scalar"
ATTR_PITCH_SCALAR = "pitch_scalar"

SAY_TEXT_FIELD_ENTITY_ID = ATTR_ENTITY_ID
