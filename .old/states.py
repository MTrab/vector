"""For handling states."""
from __future__ import annotations

FEATURES_TO_IGNORE = ["NoFeature", "SDK"]
STIMULATIONS_TO_IGNORE = ["PlacedOnCharger"]


class VectorStates(dict):
    """Handling Vector events."""
