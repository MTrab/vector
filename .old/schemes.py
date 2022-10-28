"""Defines schemes for use with Vector."""
from __future__ import annotations
import voluptuous as vol

from homeassistant.helpers import config_validation as cv

from .const import ATTR_MESSAGE, ATTR_USE_VECTOR_VOICE

TTS = vol.All(
    cv.make_entity_service_schema(
        {
            vol.Required(ATTR_MESSAGE): str,
            vol.Optional(ATTR_USE_VECTOR_VOICE, default=True): bool,
        }
    )
)
