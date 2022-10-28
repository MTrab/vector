"""For handling the randominess in Vectors chatting and responses."""
from __future__ import annotations

import logging
import os
import random
from dataclasses import dataclass
from datetime import datetime

from ha_vector import audio
from homeassistant.helpers.json import json

from .const import DATASETS, VectorDatasets
from .faces import Face, FaceDescriptor

_LOGGER = logging.getLogger(__name__)


@dataclass
class ChatterResponse:
    """Dataclass for holding chatter response."""

    min: int
    max: int
    text: str


@dataclass
class JokeResponse(ChatterResponse):
    """Dataclass for holding a joke response."""

    intro: str | None


@dataclass
class FactResponse(ChatterResponse):
    """Dataclass for holding chatter response."""

    intro: str | None
    outro: str | None


class Chatter:
    """Class for handling Vectors chatter."""

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

    # SDK volume mappings
    __vol = {
        1: audio.RobotVolumeLevel.LOW,
        2: audio.RobotVolumeLevel.MEDIUM_LOW,
        3: audio.RobotVolumeLevel.MEDIUM,
        4: audio.RobotVolumeLevel.MEDIUM_HIGH,
        5: audio.RobotVolumeLevel.HIGH,
    }

    __datasets = {}

    def __init__(
        self,
        dataset_path: str,
        chattiness: int = 5,
        volume: int = 4,
        get_face_callback: FaceDescriptor | None = None,
    ):
        """Initialize the chatter object."""

        self.__chattiness = self.__multiplier[chattiness]
        self._volume = self.__vol[volume]

        self.get_face = get_face_callback

        for data in DATASETS.items():
            if data[1]:
                _LOGGER.debug("Loading dataset %s", data[1])
                fullname = str(f"{dataset_path}/{data[1]}")
                with os.fdopen(os.open(fullname, os.O_RDONLY), "r") as file:
                    res = json.load(file)

                self.__datasets.update({data[0]: res})

    def get_text(
        self, data_type: VectorDatasets, event: str | None = None
    ) -> ChatterResponse | JokeResponse | FactResponse:
        """Get random text response."""
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
        elif data_type == VectorDatasets.FACTS:
            dataset = self.__datasets[data_type]
            intro = random.choice(dataset["fact_intro"]["sentence"])
            rand_body = random.randrange(0, len(dataset["fact_body"]["sentence"]))
            outro = random.choice(dataset["fact_end"]["sentence"])

            return FactResponse(
                dataset["fact_body"]["min"],
                dataset["fact_body"]["max"],
                dataset["fact_body"][rand_body],
                self.__substitute(intro),
                self.__substitute(outro),
            )

        else:
            dataset = self.__datasets[data_type][event]
            rand_line = random.randrange(0, len(dataset["sentence"]))
            return ChatterResponse(
                dataset["min"] * self.__chattiness,
                dataset["max"] * self.__chattiness,
                self.__substitute(dataset["sentence"][rand_line]),
            )

    def __substitute(self, text: str) -> str:
        """Substitute some strings."""
        _LOGGER.debug("Before substitution: %s", text)
        variations = self.__datasets[VectorDatasets.VARIATIONS]
        if "{name}" in text:
            face: Face = self.get_face
            if (
                face.last_seen_timestamp
                > (datetime.now() - face.last_seen_timestamp).total_seconds()
                < 5
            ):
                text = text.replace("{name}", face.last_seen_name)
            else:
                text = text.replace("{name}", "")

        text = text.format(
            good=random.choice(variations["good"]),
            scary=random.choice(variations["scary"]),
            weird=random.choice(variations["weird"]),
            interesting=random.choice(variations["interesting"]),
        )
        _LOGGER.debug("After substitution: %s", text)
        return text
