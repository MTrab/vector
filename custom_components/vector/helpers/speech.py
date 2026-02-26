"""Stuff for making Vector speech easy to handle."""

# pylint: disable=bare-except
from __future__ import annotations

import asyncio
import json
import logging
import os
import random
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
from typing import Any

from homeassistant.const import STATE_UNKNOWN
from homeassistant.core import HomeAssistant

from ..const import DOMAIN
from .connection import Connection

_LOGGER = logging.getLogger(__name__)

from .const import DATASETS, JOKE_SPEED, VectorDatasets


@dataclass
class VectorResponse:
    """Dataclass for holding default response."""

    min: int
    max: int
    text: str


@dataclass
class JokeResponse(VectorResponse):
    """Dataclass for holding a joke response."""

    intro: str | None


@dataclass
class FactResponse(VectorResponse):
    """Dataclass for holding a fact response."""

    intro: str | None
    outro: str | None


class VectorSpeechText:
    """Speech message."""

    Text: str
    Vector_Voice: bool = True
    Speed: float | int = 1.0
    Delay: float | int | None = None


class SpeechType(Enum):
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


class Speech:
    """Handle speech for Vector."""

    # Muiltipliers for Vector's chattiness - used for manipulating the time delays
    __multiplier = {
        1: 7,
        2: 4,
        3: 2,
        4: 1.35,
        5: 1,
        6: 0.8,
        7: 0.5,
        8: 0.35,
        9: 0.2,
        10: 0.1,
    }

    __chattiness = __multiplier[5]
    __last = {}

    def __init__(
        self, hass: HomeAssistant, dataset_path: str, robot: Connection
    ) -> None:
        """Initialize speech handler."""
        self.hass = hass
        self.robot = robot
        self.__datasets: dict = {}

        for data in DATASETS.items():
            if data[1]:
                _LOGGER.debug("Loading dataset %s", data[1])
                fullname = str(f"{dataset_path}/{data[1]}")
                with os.fdopen(os.open(fullname, os.O_RDONLY), "r") as file:
                    res = json.load(file)

                self.__datasets.update({data[0]: res})

    async def async_speak_predefined(
        self, predefined_speech: SpeechType, force_speech: bool = False
    ) -> datetime | None:
        """Tell Vector too speak a predefined text."""
        next_chatter = datetime.now() + timedelta(seconds=random.randint(5, 10))

        # This adds a bit of controllable randomness to some of the random dialogues
        # (jokes, telling the time, etc.)
        if predefined_speech == SpeechType.PASS:
            _LOGGER.debug(
                "Instead of attempting a random comment, I chose to pass this time..."
            )
            return next_chatter

        to_say = None
        now = datetime.now()
        if predefined_speech not in self.__last:
            self.__last[predefined_speech] = {
                "last": now - timedelta(seconds=100),
                "next": now + timedelta(seconds=random.randint(2, 15)),
            }

        if now < self.__last[predefined_speech]["next"] and not force_speech:
            return next_chatter  # Too soon to speak again

        if predefined_speech == SpeechType.JOKE:
            response: JokeResponse = self.get_text(VectorDatasets.JOKES)

            text = ""
            if len(response.intro) > 0:
                text = response.intro
            text = response.text

            joke = VectorSpeechText()
            joke.Text = text
            joke.Speed = JOKE_SPEED
            joke.Vector_Voice = True
            to_say = joke

        if isinstance(to_say, type(None)):
            return next_chatter  # Message was not set, so we skip the send action

        # if predefined_speech == SpeechType.JOKE:
        #     try:
        #         await asyncio.wrap_future(
        #             self.robot.anim.play_animation_trigger(random.choice(JOKE_ANIM))
        #         )
        #     except:
        #         pass

        await self.robot.async_speak(to_say)

        return next_chatter

    def get_text(
        self, data_type: VectorDatasets, event: str | None = None
    ) -> VectorResponse | FactResponse | JokeResponse:
        """Get a random response."""
        if data_type == VectorDatasets.JOKES:
            dataset = self.__datasets[data_type]
            intro = random.choice(dataset["joke_intro"]["sentence"])
            rand_joke = random.randrange(0, len(dataset["jokes"]))

            return JokeResponse(
                dataset["jokes"][rand_joke]["min"],
                dataset["jokes"][rand_joke]["max"],
                self.__substitute(dataset["jokes"][rand_joke]["text"]),
                self.__substitute(intro),
            )

    def __substitute(self, text: str) -> str:
        """Substitute some strings."""
        _LOGGER.debug("Before substitution: %s", text)
        variations = self.__datasets[VectorDatasets.VARIATIONS]
        if "{name}" in text:
            # face: Face = self.get_face
            # if (
            #     face.last_seen_timestamp
            #     > (datetime.now() - face.last_seen_timestamp).total_seconds()
            #     < 5
            # ):
            #     text = text.replace("{name}", face.last_seen_name)
            # else:
            text = text.replace("{name}", "")

        text = text.format(
            good=random.choice(variations["good"]),
            scary=random.choice(variations["scary"]),
            weird=random.choice(variations["weird"]),
            interesting=random.choice(variations["interesting"]),
        )
        _LOGGER.debug("After substitution: %s", text)
        return text
