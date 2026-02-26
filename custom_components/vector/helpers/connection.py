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


class VectorSpeechText:
    """Speech message."""

    Text: str
    Vector_Voice: bool = True
    Speed: float | int = 1.0
    Delay: float | int | None = None


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
        timeout: float = 2.0,
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

    async def async_speak(
        self,
        message: VectorSpeechText,
    ) -> None:
        """Make Vector Home Assistant speech handler."""
        # If Vector is doing something, don't speak
        if self.status.is_pathing:
            _LOGGER.info("I'm busy, cannot speak now...")
            return

        await self.async_take_control(level=ControlPriorityLevel.DEFAULT_PRIORITY)

        if not isinstance(message.Delay, type(None)):
            await asyncio.sleep(message.Delay)

        attempt = 0
        while attempt < MAX_ATTEMPTS:
            attempt = attempt + 1

            try:
                await asyncio.wrap_future(
                    self.behavior.say_text(
                        text=message.Text,
                        use_vector_voice=message.Vector_Voice,
                        duration_scalar=message.Speed,
                    )
                )
                break
            except:
                _LOGGER.debug(
                    "Couldn't send text to Vector, remaining tries: %s",
                    MAX_ATTEMPTS - attempt,
                )
                await asyncio.sleep(1)

            if attempt == MAX_ATTEMPTS:
                _LOGGER.error("Couldn't persuade Vector to speak :(")
                await self.async_release_control()
                self.__has_control = False
                return

        await self.async_release_control()
