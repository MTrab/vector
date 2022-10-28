"""DDL Vector constants."""
from __future__ import annotations

# Base domain
DOMAIN = "vector_robot"

# Config consts.
CONF_ID = "vector_id"
CONF_IP = "vector_ip"
CONF_SERIAL = "vector_serial"
CONF_GUID = "guid"
CONF_CERTIFICATE = "cert"

# Supported platforms
PLATFORMS = ["sensor", "button", "camera"]

# Startup banner
STARTUP = """
-------------------------------------------------------------------
Digital Dream Labs Vector integration

Version: %s
This is a custom integration
If you have any issues with this you need to open an issue here:
https://github.com/mtrab/vector_robot/issues
-------------------------------------------------------------------
"""

# ONLY ENABLE FOR DEVELOPMENT!
DO_DEBUG = True
DO_DEBUG_STATES = False

# Update signal for when updates are received from events
UPDATE_SIGNAL = "vector_update_signal_{}"

# Icon list and consts.
ICON_CUBE = "cube"
ICON_ROBOT = "robot"
ICON_FACE = "face"

VECTOR_ICON = {
    ICON_ROBOT: "mdi:robot",
    ICON_CUBE: "mdi:cube",
    ICON_FACE: "mdi:face-recognition",
}

# Service constants
SERVICE_GOTO_CHARGER = "goto_charger"
SERVICE_LEAVE_CHARGER = "leave_charger"
SERVICE_SPEAK = "speak"

# Buttons
BUTTON_GENERIC = "generic"

# Sensors
SENSOR_FACE_LAST_SEEN = "Face last seen"

# Attribs
ATTR_MESSAGE = "message"
ATTR_USE_VECTOR_VOICE = "vector_voice"

# Battery states
STATE_LOW = "low"
STATE_NORMAL = "normal"
STATE_FULL = "full"
STATE_CHARGNING = "charging"

# Translation keys
LANG_STATE = "state"
LANG_BATTERY = "battery"
LANG_STIMULI = "stimuli"
LANG_OBSERVATIONS = "observations"

# Misc. consts
STATE_TIME_STAMPED = "time_stamped_feature"
STATE_FIRMWARE_VERSION = "firmware_version"
STATE_ROBOT_BATTERY_VOLTS = "robot_battery_volts"
STATE_ROBOT_BATTERY_LEVEL = "robot_battery_level"
STATE_ROBOT_IS_CHARGNING = "robot_is_charging"
STATE_ROBOT_IS_ON_CHARGER = "robot_is_on_charger"
STATE_ROBOT_SUGGESTED_CHARGE = "robot_suggested_charge_sec"
STATE_CUBE_BATTERY_VOLTS = "cube_battery_volts"
STATE_CUBE_BATTERY_LEVEL = "cube_battery_level"
STATE_CUBE_FACTORY_ID = "cube_factory_id"
STATE_CUBE_LAST_CONTACT = "cube_last_contact"
STATE_CUBE_DETECTED = "cube_last_detected"
STATE_STIMULATION = "stimulation"
STATE_CARRYING_OBJECT = "carrying_object_id"
STATE_CARRYING_OBJECT_ON_TOP = "carrying_object_on_top_id"
STATE_HEAD_TRACKING_ID = "head_tracking_id"
STATE_FOUND_OBJECT = "found_object"
STATE_LIFT_IN_FOV = "lift_in_fov"
STATE_NO_DATA = "no_data"
STATE_ONLINE = "online"
STATE_SLEEPING = "sleeping"
STATE_CAMERA_ENABLED = "camera_stream_enabled"
STATE_POSE = "pose"
STATE_POSE_ANGLE = "pose_angle"
STATE_POSE_PITCH = "pose_pitch"
STATE_HEAD_ANGLE = "head_angle"
STATE_LIFT_HEIGHT = "lift_height"
STATE_ACCEL = "accel"
STATE_GYRO = "gyro"
STATE_PROXIMITY = "prox_data"
STATE_TOUCH = "touch_data"


# Mappings
BATTERYMAP_TO_STATE = {
    0: STATE_NO_DATA,
    1: STATE_LOW,
    2: STATE_NORMAL,
    3: STATE_FULL,
}

CUBE_BATTERYMAP_TO_STATE = {0: STATE_LOW, 1: STATE_NORMAL}

FEATURES_TO_IGNORE = ["NoFeature", "SDK"]
STIMULATIONS_TO_IGNORE = ["PlacesOnCharger"]
