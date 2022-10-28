"""Handler for Vectors observations."""
# pylint: disable=invalid-name
from __future__ import annotations

import logging

from .faces import Face

_LOGGER = logging.getLogger(__name__)


class Observations:
    """Class for holding the observations done by Vector"""

    def __init__(self) -> None:
        """Initialize the observations class."""
        super().__init__()

        self.faces = Face()
        self.objects = {}
