"""Tests for Vector domain services."""

from __future__ import annotations

import asyncio
from types import SimpleNamespace

import pytest
from homeassistant.exceptions import ServiceValidationError

from custom_components.vector import _async_handle_say_text_service
from custom_components.vector.const import (
    ATTR_DURATION_SCALAR,
    ATTR_ENTRY_ID,
    ATTR_PITCH_SCALAR,
    ATTR_TEXT,
    ATTR_USE_VECTOR_VOICE,
    DOMAIN,
)


class FakeCoordinator:
    """Coordinator stub for service tests."""

    def __init__(self) -> None:
        self.calls: list[dict[str, str | bool | float]] = []

    async def async_say_text(
        self,
        *,
        text: str,
        use_vector_voice: bool,
        duration_scalar: float,
        pitch_scalar: float,
    ) -> None:
        self.calls.append(
            {
                ATTR_TEXT: text,
                ATTR_USE_VECTOR_VOICE: use_vector_voice,
                ATTR_DURATION_SCALAR: duration_scalar,
                ATTR_PITCH_SCALAR: pitch_scalar,
            }
        )


def _hass_with_coordinators(coordinators: dict[str, FakeCoordinator]) -> SimpleNamespace:
    return SimpleNamespace(data={DOMAIN: {"coordinators": coordinators}})


def test_say_text_service_uses_single_entry_when_no_entry_id() -> None:
    coordinator = FakeCoordinator()
    hass = _hass_with_coordinators({"entry-1": coordinator})

    asyncio.run(
        _async_handle_say_text_service(
            hass,
            {
                ATTR_TEXT: "Hej Vector",
            },
        )
    )

    assert coordinator.calls == [
        {
            ATTR_TEXT: "Hej Vector",
            ATTR_USE_VECTOR_VOICE: True,
            ATTR_DURATION_SCALAR: 1.0,
            ATTR_PITCH_SCALAR: 0.0,
        }
    ]


def test_say_text_service_rejects_missing_entry_id_when_multiple_entries() -> None:
    hass = _hass_with_coordinators(
        {"entry-1": FakeCoordinator(), "entry-2": FakeCoordinator()}
    )

    with pytest.raises(ServiceValidationError):
        asyncio.run(_async_handle_say_text_service(hass, {ATTR_TEXT: "Hej"}))


def test_say_text_service_rejects_unknown_entry_id() -> None:
    hass = _hass_with_coordinators({"entry-1": FakeCoordinator()})

    with pytest.raises(ServiceValidationError):
        asyncio.run(
            _async_handle_say_text_service(
                hass,
                {
                    ATTR_ENTRY_ID: "missing",
                    ATTR_TEXT: "Hej",
                },
            )
        )
