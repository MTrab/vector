"""Stuff for making Vector speech easy to handle."""
# pylint: disable=bare-except
from __future__ import annotations

import asyncio
import logging
import random
from datetime import datetime, timedelta
from enum import Enum
from typing import Any

from homeassistant.const import STATE_UNKNOWN
from homeassistant.core import HomeAssistant

from . import VectorHandler, VectorSpeechText
from .chatter import Chatter, ChatterResponse, FactResponse, JokeResponse
from .const import (
    FACT_SPEED,
    JOKE_ANIM,
    JOKE_SPEED,
    NEWS_SPEED,
    WEATHER_SPEED,
    VectorDatasets,
)

_LOGGER = logging.getLogger(__name__)


class VectorSpeechType(Enum):
    """Supported types of Speech."""

    PASS = "pass"  # Do nothing
    CUSTOM = "custom"  # Custom text
    PETTING = "petting"  # When petting has started
    CLIFF = "cliff"  # When finding a "cliff" or other noticable color change
    GREETING = "greeting"  # Greeting
    DROP = "drop"  # When dropped or falling
    JOKE = "joke"  # Tell a random joke
    WAKE_WORD = "wake_word"  # When wake word (Hey Vector) was heard
    INVALID = "invalid"  # When Vector doesn't understand what he was told/asked
    FACT = "fact"  # Tell a random fact
    TIME = "time"  # Tell the current time
    WEATHER = "weather"  # Tell the weather forecast
    HELD = "picked_up"  # Vector is being held (picked up)
    CHARGING = "charging"  # When Vector is in the charging pad
    SLEEPING = "sleeping"  # When Vector status is sleeping
    BLOCK_DROPPED = "dropped_block"  # When the block is dropped or put down
    BUTTON_PRESSED = "button_pressed"  # When you press Vectors button
    NEWS = "news"  # Read some news
    NEWS_INTRO = "news_intro"  # Read news
    OBJECT_DETECTED = "object_detected"  # When an object detected


class VectorSpeech:
    """Vector speech class."""

    __last = {}
    __dataset: str

    def __init__(
        self,
        hass: HomeAssistant,
        robot: VectorHandler,
        dataset,
        random_chatter: bool = False,
        state_callback: Any = None,
        faces_callback: Any = None,
    ) -> None:
        """Initialize a speech class."""
        self.hass = hass
        self.robot = robot
        self.__dataset = dataset
        self.get_state = state_callback
        self.get_face = faces_callback
        self._random_chatter = random_chatter

    async def async_random_chatting(self, *args, **kwargs) -> datetime | bool:
        """Handle some random chatter when Vector is awake.

        Returns:
        datetime: Timedelta object for when try chatting next time.
        bool: Returns False if we cannot get the current state of Vector.
        """
        if isinstance(self.get_state, type(None)):
            return False  # No state callback was set, so we can't check

        next_chatter = datetime.now() + timedelta(seconds=random.randint(5, 10))

        try:
            bot_state = self.get_state()
        except AttributeError:
            # No connection so we skip further code.
            return next_chatter

        if bot_state in ["sleeping", STATE_UNKNOWN]:
            # Vector is sleeping or in an unknown state, so don't make him speak.
            _LOGGER.debug("Random chatter got state %s so we are skipping", bot_state)
            return next_chatter

        chatter_type = random.choices(
            ["pass", "joke", "fact", "time"],  # "weather"],
            [60, 20, 10, 10],  # 5],
            k=1,
        )

        await self.async_speak(predefined=VectorSpeechType(chatter_type))

        return next_chatter

    async def async_speak(
        self,
        text: str | None = None,
        predefined: VectorSpeechType = VectorSpeechType.CUSTOM,
        use_vector_voice: bool = True,
        speed: float = 1.0,
        force_speech: bool = False,
    ) -> datetime | None:
        """Routing for making Vector speak."""
        _LOGGER.debug("Predefine called: %s", predefined)

        next_chatter = datetime.now() + timedelta(seconds=random.randint(5, 10))

        # This adds a bit of controllable randomness to some of the random dialogues
        # (jokes, telling the time, etc.)
        if predefined == VectorSpeechType.PASS:
            _LOGGER.debug(
                "Instead of attempting a random comment, I chose to pass this time..."
            )
            return next_chatter

        to_say = None
        now = datetime.now()
        if predefined not in self.__last:
            self.__last[predefined] = {
                "last": now - timedelta(seconds=100),
                "next": now + timedelta(seconds=random.randint(2, 15)),
            }

        if now < self.__last[predefined]["next"] and not force_speech:
            return next_chatter  # Too soon to speak again

        if predefined == VectorSpeechType.CUSTOM:
            msg = VectorSpeechText()
            msg.Text = text
            msg.Speed = speed
            msg.Vector_Voice = use_vector_voice
            to_say = msg

            self.__last[predefined] = {
                "last": now,
                "next": now + timedelta(seconds=random.randint(2, 15)),
            }
        elif predefined == VectorSpeechType.JOKE:
            chatter = Chatter(self.__dataset, get_face_callback=self.get_face)
            response: JokeResponse = chatter.get_text(VectorDatasets.JOKES)

            text = ""
            if len(response.intro) > 0:
                text = response.intro
            text = response.text

            joke = VectorSpeechText()
            joke.Text = text
            joke.Speed = JOKE_SPEED
            joke.Vector_Voice = use_vector_voice
            to_say = joke
        elif predefined == VectorSpeechType.FACT:
            chatter = Chatter(self.__dataset, get_face_callback=self.get_face)
            response: FactResponse = chatter.get_text(VectorDatasets.FACTS)

            text = ""
            if len(response.intro) > 0:
                text = response.intro
            text = response.text
            if len(response.outro) > 0:
                text += response.outro

            fact = VectorSpeechText()
            fact.Text = text
            fact.Speed = FACT_SPEED
            fact.Vector_Voice = use_vector_voice
            to_say = fact
        else:
            chatter = Chatter(self.__dataset, get_face_callback=self.get_face)
            response: ChatterResponse = chatter.get_text(
                VectorDatasets.DIALOGS, predefined.value
            )
            msg = VectorSpeechText()
            msg.Text = response.text
            msg.Speed = speed
            msg.Vector_Voice = use_vector_voice
            to_say = msg

            self.__last[predefined] = {
                "last": now,
                "next": now
                + timedelta(seconds=random.randint(response.min, response.max)),
            }

        if isinstance(to_say, type(None)):
            return next_chatter  # Message was not set, so we skip the send action

        _LOGGER.debug("Sending %s", to_say)
        await self.robot.async_speak(
            message=to_say,
        )

        if predefined == VectorSpeechType.JOKE:
            try:
                await asyncio.wrap_future(
                    self.robot.anim.play_animation_trigger(random.choice(JOKE_ANIM))
                )
            except:
                pass

        return next_chatter
