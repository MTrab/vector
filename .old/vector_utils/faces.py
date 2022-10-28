"""Handling detected faces."""
from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime

_LOGGER = logging.getLogger(__name__)


@dataclass
class FaceDescriptor:
    """Description of face properties."""

    id: int  # pylint: disable=invalid-name
    name: str
    expression: str
    expression_score: int
    last_seen: datetime = None

    def __post_init__(self) -> None:
        """Set last_seen on generation"""
        self.last_seen = datetime.now()


class Face:
    """Handling detected faces."""

    last_seen_face: FaceDescriptor = None

    def __init__(self) -> None:
        """Initialize the handler."""
        self._known_faces: dict[int, FaceDescriptor] = {}

    def saw_face(
        self, face_id: int, name: str, expression: str, expression_score: int
    ) -> None:
        """When Vector sees a face."""
        seen = FaceDescriptor(face_id, name, expression, expression_score)
        self._known_faces.update({face_id: seen})
        self.last_seen_face = seen

    @property
    def last_seen_timestamp(self) -> datetime | bool:
        """Get the last seen timestamp or False if nobody have been recognized yet."""
        return (
            self.last_seen_face.last_seen
            if not isinstance(self.last_seen_face, type(None))
            else False
        )

    @property
    def last_seen_name(self) -> str | bool:
        """Get the last seen name or False if nobody have been recognized yet."""
        return (
            self.last_seen_face.name
            if not isinstance(self.last_seen_face, type(None))
            else False
        )

    def get_by_id(self, face_id: int) -> FaceDescriptor | bool:
        """Get a known face by ID.

        Returns
        FaceDescriptor: If a face is in the known dict, this is returned.
        False: If we have no record of seeing this face ID we return False.
        """
        return self._known_faces[face_id] if face_id in self._known_faces else False

    def get_by_name(self, name: str) -> FaceDescriptor | bool:
        """Get a known face by name.

        Returns
        FaceDescriptor: If a face is in the known dict, this is returned.
        False: If we have no record of seeing this face name we return False.
        """

        for known_face in self._known_faces:
            if known_face.name == name:
                return known_face

        return False

    @property
    def known_faces(self) -> dict:
        """Returns a dict of all known faces."""
        return self._known_faces
