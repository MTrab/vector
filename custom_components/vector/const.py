"""Vector robot consts."""

# Startup banner
BANNER = """
-------------------------------------------------------------------
Digital Dream Labs Vector (Anki Vector)
Version: %s
This is a custom integration
If you have any issues with this you need to open an issue here:
https://github.com/mtrab/vector/issues
-------------------------------------------------------------------
"""

# Integration specific CONF_ attributes
CONF_CERTIFICATE = "certificate"
CONF_ESCAPEPOD = "escapepod"
CONF_GUID = "guid"
CONF_IP = "ip_address"
CONF_SERIAL = "serial_number"

# Integration base domain
DOMAIN = "vector"

# Icon consts.
ICON_CUBE = "cube"
ICON_ROBOT = "robot"
ICON_FACE = "face"

# Translation keys
LANG_STATE = "state"
LANG_BATTERY = "battery"
LANG_STIMULI = "stimuli"
LANG_OBSERVATIONS = "observations"
LANG_FACE = "face"

# States
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
STATE_LAST_FACE = "last_face"
STATE_LAST_FACE_TIMESTAMP = "last_face_TIMESTAMP"
STATE_LAST_KNOWN_FACE = "last_known_face"
STATE_LAST_KNOWN_FACE_ID = "last_known_face_id"
STATE_LAST_KNOWN_FACE_TIMESTAMP = "last_known_face_timestamp"
STATE_UNKNOWN_FACE = "unknown_face"
STATE_NO_FACE = "no_face_detected"
STATE_LOW = "low"
STATE_NORMAL = "normal"
STATE_FULL = "full"
STATE_CHARGNING = "charging"
