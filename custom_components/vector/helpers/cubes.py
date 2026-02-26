"""Class for handling cubes and cubes states."""

from __future__ import annotations

import logging
from collections.abc import Callable
from datetime import datetime, timedelta
from typing import Any

import pytz
from homeassistant.config_entries import ConfigEntries
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.dispatcher import async_dispatcher_send
from homeassistant.util import dt as dt_utils

from ..const import DOMAIN, SIGNAL_CUBE_ADD, SIGNAL_CUBE_UPDATE
from ..exceptions import UnknownCubeException

_LOGGER = logging.getLogger(__name__)


class Cube:
    """Define a single cube class."""

    __id: str = None
    __level: str = None
    __voltage: float = 0
    __last_seen: datetime = None
    __seen_by: str = None
    __added: bool = False
    __battery_level: int = 0

    def __init__(self, data: Any) -> None:
        """Initialize the cube class."""
        self.__id = data.factory_id
        self.__level = data.level
        self.__voltage = round(data.battery_volts, 2)
        self.__last_seen = dt_utils.utcnow() - timedelta(
            seconds=int(data.time_since_last_reading_sec)
        )
        bat_level = int(round((self.__voltage - 1) * 200, 0))
        if bat_level > 100:
            bat_level = 100
        elif bat_level < 0:
            bat_level = 0

        self.__battery_level = bat_level

    @property
    def level(self) -> str:
        """Get battery level as a string (Response is Normal or Low)."""
        return self.__level

    @property
    def voltage(self) -> float:
        """Return the voltage."""
        return self.__voltage

    @property
    def battery_level(self) -> float:
        """Return the voltage."""
        return self.__battery_level

    @property
    def last_seen(self) -> datetime:
        """Return the timestamp for last contact."""
        return self.__last_seen.isoformat()

    @property
    def id(self) -> str:
        """Return the ID (Bluetooth MAC) of the cube."""
        return self.__id

    @property
    def last_seen_by(self) -> str:
        """Last seen by this robot."""
        return self.__seen_by

    @last_seen_by.setter
    def last_seen_by(self, value):
        """Set the last seen by property."""
        self.__seen_by = value

    @property
    def added(self) -> None:
        """Is this cube added as device?"""
        return self.__added

    @added.setter
    def added(self, value):
        """Set added flag."""
        self.__added = value


class Cubes:
    """Define Cubes class."""

    __cubes: dict = {}

    def __init__(self, hass: HomeAssistant, entry_id) -> None:
        """Initialize the class."""
        self.hass = hass
        self.entry_id = entry_id

    def async_check_cube_config(
        self, cube: Cube, callbacks: list[Callable[[int], None]] = []
    ) -> None:
        """Check if Cube device exists."""
        dreg = dr.async_get(self.hass)
        identifiers = {(DOMAIN, f"cube_{cube.id}")}
        connections = {(dr.CONNECTION_NETWORK_MAC, cube.id)}

        dreg.async_get_or_create(
            config_entry_id=self.entry_id,
            identifiers=identifiers,
            connections=connections,
            name=f"Vector Cube {cube.id}",
            model="Vector Cube",
        )

        for callback in callbacks:
            _LOGGER.debug("Dispatching callback for cube %s", cube.id)
            callback(cube.id)

    def update(
        self, data: Any, seen_by: str, hass, callbacks: list[Callable[[int], None]] = []
    ) -> None:
        """Update the state of a cube."""
        if data.factory_id == "":
            return

        cube = Cube(data)
        cube.last_seen_by = seen_by

        try:
            self.async_check_cube_config(cube, callbacks)
        except:
            pass

        if (
            cube.id in self.__cubes
            and self.__cubes[cube.id] != seen_by
            and cube.last_seen > self.__cubes[cube.id].last_seen
        ):
            _LOGGER.debug(
                "Cube %s was seen by another robot, updating last seen",
                cube.id,
            )
            self.__cubes.update({cube.id: cube})
        elif cube.id not in self.__cubes:
            _LOGGER.debug(
                "Cube %s was unknown, adding to the list",
                cube.id,
            )
            self.__cubes.update({cube.id: cube})

        _LOGGER.debug(
            "Dispatching '%s' update signal", SIGNAL_CUBE_UPDATE.format(cube.id)
        )
        async_dispatcher_send(self.hass, SIGNAL_CUBE_UPDATE.format(cube.id), cube.id, hass)

    @property
    def all_cubes(self) -> dict:
        """Returns a dictionary of all known cubes."""
        return self.__cubes

    def get_cube(self, cube_id: str) -> Cube:
        """Get a specific cube."""
        if cube_id in self.__cubes:
            return self.__cubes[cube_id]

        raise UnknownCubeException()
