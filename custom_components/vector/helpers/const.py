"""Consts for the data runner."""
from __future__ import annotations
from enum import IntEnum

BASE_URL = "https://raw.githubusercontent.com/MTrab/vector/development-v1/Datasets/{}"


class VectorDatasets(IntEnum):
    """Vector dataset enum."""

    VARIATIONS = 0
    DIALOGS = 1
    JOKES = 2
    FACTS = 3
    WEATHER = 4


DATASETS = {
    VectorDatasets.DIALOGS: "dialog.json",
    VectorDatasets.FACTS: "facts.json",
    VectorDatasets.JOKES: "jokes.json",
    VectorDatasets.VARIATIONS: "variations.json",
    VectorDatasets.WEATHER: None,
}

JOKE_ANIM = [
    "GreetAfterLongTime",
    "ComeHereSuccess",
    "OnboardingReactToFaceHappy",
    "PickupCubeSuccess",
    "PounceSuccess",
    "ConnectToCubeSuccess",
    "FetchCubeSuccess",
    "FistBumpSuccess",
    "OnboardingWakeWordSuccess",
]

JOKE_SPEED = 1.15
FACT_SPEED = 1.15
NEWS_SPEED = 1.15
WEATHER_SPEED = 1.15
