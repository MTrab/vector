"""Vector connector handler."""
# pylint: disable=bare-except,unused-argument
from __future__ import annotations
import asyncio
import logging

from ha_vector import AsyncRobot
from ha_vector.connection import ControlPriorityLevel, on_connection_thread, protocol

_LOGGER = logging.getLogger(__name__)

# Sometimes Vector doesn't like to respond to commands, lets try again MAX_ATTEMPTS times.
MAX_ATTEMPTS = 10


class Connection(AsyncRobot):
    """Custom handler for Vector actions."""

    __has_control: bool = False

    async def async_take_control(
        self,
        level: ControlPriorityLevel | None = None,
        timeout: float = 1.0,
    ) -> None:
        """Take control of Vectors behavior."""
        if not self.__has_control:
            attempt = 0
            while attempt < MAX_ATTEMPTS and not self.__has_control:
                attempt = attempt + 1

                try:
                    await asyncio.wrap_future(
                        self.conn.request_control(
                            behavior_control_level=level, timeout=timeout
                        )
                    )
                    self.__has_control = True
                    return
                except TypeError as exc:
                    raise TypeError() from exc
                except:
                    _LOGGER.debug(
                        "Couldn't get robot control, remaining tries: %s",
                        MAX_ATTEMPTS - attempt,
                    )
                    await asyncio.sleep(1)

            if attempt == MAX_ATTEMPTS:
                _LOGGER.error("Couldn't persuade Vector to be controlled :(")
                await self.async_release_control()
                self.__has_control = False

    async def async_release_control(
        self,
        timeout: float = 1.0,
    ) -> None:
        """Take control of Vectors behavior."""
        if self.__has_control:
            attempt = 0
            while attempt < MAX_ATTEMPTS and self.__has_control:
                attempt = attempt + 1

                try:
                    await asyncio.wrap_future(
                        self.conn.release_control(timeout=timeout)
                    )
                    self.__has_control = False
                    return
                except:
                    _LOGGER.debug(
                        "Couldn't release robot control, remaining tries: %s",
                        MAX_ATTEMPTS - attempt,
                    )
                    await asyncio.sleep(1)
