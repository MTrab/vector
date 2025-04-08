"""Vector states handler."""

from __future__ import annotations

import datetime
import logging
import math
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import STATE_UNKNOWN
from homeassistant.core import HomeAssistant
from homeassistant.helpers.dispatcher import dispatcher_send

from ..const import (
    STATE_ACCEL,
    STATE_ALIVE_DISTANCE,
    STATE_ALIVE_PET_MS,
    STATE_ALIVE_SECONDS,
    STATE_ALIVE_SENSOR_SCORE,
    STATE_ALIVE_TRIGGERWORDS,
    STATE_CAMERA_ENABLED,
    STATE_CARRYING_OBJECT,
    STATE_CARRYING_OBJECT_ON_TOP,
    STATE_CUBE_BATTERY_VOLTS,
    STATE_CUBE_FACTORY_ID,
    STATE_CUBE_LAST_CONTACT,
    STATE_FIRMWARE_VERSION,
    STATE_GYRO,
    STATE_HEAD_ANGLE,
    STATE_HEAD_TRACKING_ID,
    STATE_LIFT_HEIGHT,
    STATE_POSE,
    STATE_POSE_ANGLE,
    STATE_POSE_PITCH,
    STATE_PROXIMITY,
    STATE_ROBOT_BATTERY_VOLTS,
    STATE_ROBOT_IS_CHARGNING,
    STATE_ROBOT_IS_ON_CHARGER,
    STATE_ROBOT_SUGGESTED_CHARGE,
    STATE_STIMULATION,
    STATE_TOUCH,
    UPDATE_SIGNAL,
)
from ..helpers.images import convert_pil_image_to_byte_array

MAXVOLTAGE = 4.1
MIDVOLTAGE = 3.85
MINVOLTAGE = 3.5

_LOGGER = logging.getLogger(__name__)


class VectorRobotState:
    """A Vector robot state class."""

    def __init__(self, attributes: list | None) -> None:
        """Initialize the state handler."""
        self.state: str = STATE_UNKNOWN
        self.attributes: dict = {}

        for attribute in attributes:
            self.attributes.update({attribute: None})


class VectorCubeBattery:
    """Handler for a cube battery."""

    def __init__(self) -> None:
        """Initialize a cube battery."""
        self._cubes: dict = {}


class VectorBatteries:
    """Battery handler class."""

    def __init__(self) -> None:
        """Initialize the batteries object"""
        self.robot: VectorRobotState = VectorRobotState(
            attributes=[
                STATE_ROBOT_BATTERY_VOLTS,
                STATE_ROBOT_IS_CHARGNING,
                STATE_ROBOT_IS_ON_CHARGER,
                STATE_ROBOT_SUGGESTED_CHARGE,
            ]
        )
        self.cubes: VectorRobotState = VectorRobotState(
            attributes=[
                STATE_CUBE_BATTERY_VOLTS,
                STATE_CUBE_FACTORY_ID,
                STATE_CUBE_LAST_CONTACT,
            ]
        )


class States:
    """State handler."""

    def __init__(self, coordinator) -> None:
        """Initialize the handler."""
        from ..coordinator import (  # pylint: disable=import-outside-toplevel
            VectorDataUpdateCoordinator,
        )

        # Local used attrs

        self.coordinator: VectorDataUpdateCoordinator = coordinator
        self.entry: ConfigEntry = coordinator.entry
        self.hass: HomeAssistant = coordinator.hass
        self.name = coordinator.name
        self._batteries: VectorBatteries = VectorBatteries()
        self._robot_state: VectorRobotState = VectorRobotState(
            attributes=[
                STATE_FIRMWARE_VERSION,
                STATE_STIMULATION,
                STATE_CARRYING_OBJECT,
                STATE_CARRYING_OBJECT_ON_TOP,
                STATE_HEAD_TRACKING_ID,
                STATE_CAMERA_ENABLED,
                STATE_POSE,
                STATE_POSE_ANGLE,
                STATE_POSE_PITCH,
                STATE_HEAD_ANGLE,
                STATE_LIFT_HEIGHT,
                STATE_ACCEL,
                STATE_GYRO,
                STATE_PROXIMITY,
                STATE_TOUCH,
                STATE_ALIVE_SECONDS,
                STATE_ALIVE_TRIGGERWORDS,
                STATE_ALIVE_PET_MS,
                STATE_ALIVE_DISTANCE,
                STATE_ALIVE_SENSOR_SCORE,
            ]
        )

        # Global used attrs
        self.observations = None

        # Used for camera images
        self.got_image = False
        self._last_image: bytes | None = None

    @property
    def last_image(self) -> bytes | None:
        """RRepresents the last image received from Vector."""
        return self._last_image

    @last_image.setter
    def last_image(self, value: Any) -> None:
        """Set last_image property."""
        self._last_image = convert_pil_image_to_byte_array(value)

    def robot_battery_state(self, value: str | None = None) -> str | None:
        """Returns the robot battery state."""
        if isinstance(value, type(None)):
            return self._batteries.robot.state

        _LOGGER.debug("Setting robot battery state: %s", value)
        self._batteries.robot.state = value

        return None

    def get_robot_battery_attributes(self, attributes: dict | str | None):
        """Return all attributes or just the ones in the dictionary."""
        if isinstance(attributes, type(None)):
            return self._batteries.robot.attributes

        if isinstance(attributes, dict):
            attribute_list = {}
            for attr, name in attributes.items():
                attribute_list.update({name: self._batteries.robot.attributes[attr]})

            return attribute_list
        else:
            _LOGGER.debug("Returning %s from attributes", attribute_list[attributes])
            return attribute_list[attributes]

    def robot_battery_attributes(
        self, attribute: str | dict | None = None, value: Any | None = None
    ) -> dict | Any | None:
        """Returns the robot battery attributes."""
        if isinstance(value, type(None)) and not isinstance(attribute, dict):
            return (
                self._batteries.robot.attributes
                if isinstance(attribute, type(None))
                else (
                    self._batteries.robot.attributes[attribute]
                    if attribute in self._batteries.robot.attributes
                    else STATE_UNKNOWN
                )
            )

        if isinstance(attribute, dict):
            _LOGGER.debug("Setting robot battery attributes:\n%s", value)
            self._batteries.robot.attributes = value
        else:
            _LOGGER.debug("Setting robot battery attribute '%s': %s", attribute, value)
            self._batteries.robot.attributes.update({attribute: value})

        return None

    def cube_battery_state(self, value: str | None = None) -> str | None:
        """Returns the cube battery state."""
        if isinstance(value, type(None)):
            return self._batteries.cubes.state

        _LOGGER.debug("Setting cube battery state: %s", value)
        self._batteries.cubes.state = value
        return None

    def get_cube_battery_attributes(self, attributes: dict | None):
        """Return all attributes or just the ones in the dictionary."""
        if isinstance(attributes, type(None)):
            return self._batteries.cubes.attributes

        attribute_list = {}
        for attr, name in attributes.items():
            attribute_list.update({name: self._batteries.cubes.attributes[attr]})

        return attribute_list

    def cube_battery_attributes(
        self, attribute: str | dict | None = None, value: Any | None = None
    ) -> dict | Any | None:
        """Returns the cube battery attributes."""
        if isinstance(value, type(None)) and not isinstance(attribute, dict):
            return (
                self._batteries.cubes.attributes
                if isinstance(attribute, type(None))
                else (
                    self._batteries.cubes.attributes[attribute]
                    if attribute in self._batteries.cubes.attributes
                    else STATE_UNKNOWN
                )
            )

        if isinstance(attribute, dict):
            _LOGGER.debug("Setting cube battery attributes:\n%s", value)
            self._batteries.cubes.attributes = value
        else:
            _LOGGER.debug("Setting cube battery attribute '%s': %s", attribute, value)
            self._batteries.cubes.attributes.update({attribute: value})

        return None

    @property
    def robot_battery_percentage(self) -> int:
        """Get the battery level in percent."""
        voltage = self._batteries.robot.attributes[STATE_ROBOT_BATTERY_VOLTS]
        percent = 0
        if voltage >= MAXVOLTAGE:
            percent = 100
        elif voltage >= MIDVOLTAGE:
            scaled = (voltage - MIDVOLTAGE) / (MAXVOLTAGE - MIDVOLTAGE)
            percent = 80 + 20 * math.log10(1 + scaled * 9)
        elif voltage >= MINVOLTAGE:
            scaled = (voltage - MIDVOLTAGE) / (MAXVOLTAGE - MIDVOLTAGE)
            percent = 80 * math.log10(1 + scaled * 9)
        elif isinstance(voltage, type(None)):
            percent = 70
        else:
            percent = 0

        return int(percent)

    @property
    def robot_distance(self) -> str:
        """Get the distance driven by the robot."""
        return self._robot_state.attributes[STATE_ALIVE_DISTANCE]

    @property
    def robot_age(self) -> datetime:
        """Get the age of the robot."""
        _LOGGER.debug(vars(self._robot_state))
        return datetime.timedelta(
            seconds=self._robot_state.attributes[STATE_ALIVE_SECONDS]
        )

    @property
    def robot_state(self) -> str:
        """Return the robot state."""
        return (
            self._robot_state.state
            if not isinstance(self._robot_state.state, type(None))
            else STATE_UNKNOWN
        )

    def set_robot_state(self, value: str) -> None:
        """Return or set the robot state."""
        self._robot_state.state = value
        dispatcher_send(
            self.hass,
            UPDATE_SIGNAL.format("robot", self.coordinator.name, "robot_status"),
        )

    def get_robot_attributes(self, attributes: dict | str | None):
        """Return all attributes, one specific or just the ones in the dictionary."""
        if isinstance(attributes, type(None)):
            return self._robot_state.attributes

        if isinstance(attributes, str):
            return (
                self._robot_state.attributes[attributes]
                if attributes in self._robot_state.attributes
                else STATE_UNKNOWN
            )

        attribute_list = {}
        for attr, name in attributes.items():
            attribute_list.update(
                {
                    name: (
                        self._robot_state.attributes[attr]
                        if attr in self._robot_state.attributes
                        else STATE_UNKNOWN
                    )
                }
            )

        return attribute_list

    def set_robot_attribute(self, attribute: str, value: Any) -> None:
        """Set robot attribute."""
        if self._robot_state.attributes[attribute] == value:
            return

        self._robot_state.attributes.update({attribute: value})
