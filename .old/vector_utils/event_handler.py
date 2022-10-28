"""Vector events handler."""
# pylint: disable=unused-argument
from __future__ import annotations

import logging
from typing import Any

from ha_vector import Robot
from ha_vector.events import Events
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.dispatcher import async_dispatcher_send

from ..const import (
    DO_DEBUG_STATES,
    STATE_ACCEL,
    STATE_CAMERA_ENABLED,
    STATE_CARRYING_OBJECT,
    STATE_GYRO,
    STATE_HEAD_TRACKING_ID,
    STATE_LIFT_HEIGHT,
    STATE_STIMULATION,
    UPDATE_SIGNAL,
)
from ..coordinator import VectorDataUpdateCoordinator
from ..states import FEATURES_TO_IGNORE, STIMULATIONS_TO_IGNORE

_LOGGER = logging.getLogger(__name__)

EVENTS = {
    Events.new_camera_image: "on_image",
    Events.robot_state: "on_robot_state",
    Events.time_stamped_status: "on_robot_time_stamped_status",
    Events.stimulation_info: "on_robot_stimulation",
}


class VectorEvent:
    """Class for handling event subscription and data."""

    def __init__(
        self,
        hass: HomeAssistant,
        entry: ConfigEntry,
        coordinator: VectorDataUpdateCoordinator,
    ) -> None:
        """Initialize the event handlers."""
        self.coordinator = coordinator
        self.entry = entry
        self.hass = hass
        self.got_map = False
        self.navigation_map = None

    async def async_subscribe(self, event: Events = None, func: Any = None) -> None:
        """Subscribe to specific event."""
        if isinstance(event, type(None)):
            for event, func in EVENTS.items():
                await self.async_subscribe(event, getattr(self, func))
        else:
            self.coordinator.robot.events.subscribe(func, event)

    async def async_unsubscribe(self, event: Events = None, func: Any = None) -> None:
        """Unsubscribe from event(s)."""
        if isinstance(event, type(None)):
            for event, func in EVENTS.items():
                try:
                    await self.async_unsubscribe(event, getattr(self, func))
                finally:
                    pass
        else:
            self.coordinator.robot.events.unsubscribe(func, event)

    async def on_robot_time_stamped_status(
        self, robot: Robot, event_type, event, *args, **kwargs
    ):
        """Handle time stamped events (robot state)."""
        if event.status.feature_status.feature_name:
            if not event.status.feature_status.feature_name in FEATURES_TO_IGNORE:
                # feature = str(event.status.feature_status.feature_name)
                feature = str(event.status.feature_status.feature_name)
                _LOGGER.debug("Set robot state: %s", feature)
                self.coordinator.states.set_robot_state(feature.lower())

    async def on_robot_stimulation(
        self, robot: Robot, event_type, event, *args, **kwargs
    ):
        """Handle robot_state events."""
        # emotion_events: "PettingStarted"
        # emotion_events: "PettingBlissLevelIncrease"
        # emotion_events: "ReactToSoundAwake"
        if not event.emotion_events:
            return

        myevent = event.emotion_events[0]
        _LOGGER.debug("Stimulation event: %s", event)
        _LOGGER.debug("Event data:\n%s", myevent)
        if not myevent in STIMULATIONS_TO_IGNORE:
            self.coordinator.states.set_robot_attribute(
                STATE_STIMULATION, str(myevent).lower()
            )

            async_dispatcher_send(
                self.hass, UPDATE_SIGNAL.format(self.coordinator.name)
            )

        # if myevent in ["PettingStarted", "PettingBlissLevelIncrease"]:
        #     await self.speak.async_speak(predefined=VectorSpeechType.PETTING)

    async def on_robot_state(self, robot: Robot, event_type, event, *args, **kwargs):
        """Update robot states."""
        if DO_DEBUG_STATES:
            print(str(event))

        if hasattr(event, "carrying_object_id"):
            self.coordinator.states.set_robot_attribute(
                STATE_CARRYING_OBJECT, event.carrying_object_id or None
            )

        if hasattr(event, "head_tracking_object_id"):
            self.coordinator.states.set_robot_attribute(
                STATE_HEAD_TRACKING_ID, event.head_tracking_object_id or None
            )

        if hasattr(event, "gyro"):
            self.coordinator.states.set_robot_attribute(
                STATE_GYRO,
                {
                    "x": round(float(event.gyro.x), 3),
                    "y": round(float(event.gyro.y), 3),
                    "z": round(float(event.gyro.z), 3),
                },
            )

        if hasattr(event, "accel"):
            self.coordinator.states.set_robot_attribute(
                STATE_ACCEL,
                {
                    "x": round(float(event.accel.x), 3),
                    "y": round(float(event.accel.y), 3),
                    "z": round(float(event.accel.z), 3),
                },
            )

        if hasattr(event, "lift_height_mm"):
            self.coordinator.states.set_robot_attribute(
                STATE_LIFT_HEIGHT, round(float(event.lift_height_mm), 2)
            )

        self.coordinator.states.set_robot_attribute(
            STATE_CAMERA_ENABLED, bool(robot.camera.image_streaming_enabled())
        )

    # Event: pose {
    #   x: -81.23602294921875
    #   y: -114.03437805175781
    #   z: 2.5920803546905518
    #   q0: 0.9856083989143372
    #   q3: 0.16904449462890625
    #   origin_id: 7
    # }
    # pose_angle_rad: 0.3397202789783478
    # pose_pitch_rad: -0.11033941805362701
    # head_angle_rad: -0.36896002292633057
    # lift_height_mm: 32.0
    # accel {
    #   x: -4641.689453125
    #   y: 185.6196746826172
    #   z: 8891.78125
    # }
    # gyro {
    #   x: 0.00019037630409002304
    #   y: -0.0008325017988681793
    #   z: 5.6976965424837545e-05
    # }
    # carrying_object_id: -1
    # carrying_object_on_top_id: -1
    # head_tracking_object_id: -1
    # last_image_time_stamp: 51894009
    # status: 1056512
    # prox_data {
    #   distance_mm: 248
    #   signal_quality: 0.010212385095655918
    # }
    # touch_data {
    #   raw_touch_value: 4634
    # }

    def on_image(self, robot: Robot, event_type, event, *args, **kwargs):
        """Called when Vector receives a new image."""
        # _LOGGER.debug("Got new image from Vector")
        self.coordinator.states.got_image = True
        annotated_image = event.image.annotate_image()
        # self.last_image = convert_pil_image_to_byte_array(annotated_image)
        # self.coordinator.states.last_image = event.image.raw_image
        self.coordinator.states.last_image = annotated_image
