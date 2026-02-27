"""Tests for Vector number entities."""

from __future__ import annotations

import asyncio
from types import SimpleNamespace

from custom_components.vector.const import CONF_HOST, CONF_ROBOT_NAME
from custom_components.vector.number import (
    VectorCustomEyeColorHueNumber,
    VectorCustomEyeColorSaturationNumber,
)


class FakeCoordinator:
    """Simple coordinator stub for number entity tests."""

    def __init__(self) -> None:
        self.eye_color_custom_hue: float | None = 0.3
        self.eye_color_custom_saturation: float | None = 0.7
        self.calls: list[tuple[float, float]] = []

    def async_add_listener(self, update_callback):
        del update_callback
        return lambda: None

    async def async_set_custom_eye_color(
        self,
        *,
        hue: float,
        saturation: float,
    ) -> None:
        self.calls.append((hue, saturation))
        self.eye_color_custom_hue = hue
        self.eye_color_custom_saturation = saturation


def _entry(data: dict[str, str], entry_id: str = "entry-1") -> SimpleNamespace:
    return SimpleNamespace(data=data, entry_id=entry_id)


def test_custom_eye_color_hue_number_maps_state_and_updates_coordinator() -> None:
    coordinator = FakeCoordinator()
    entry = _entry({CONF_ROBOT_NAME: "Vector-ABCD", CONF_HOST: "192.168.1.10"})
    entity = VectorCustomEyeColorHueNumber(coordinator, entry)

    assert entity.native_value == 0.3
    assert entity.entity_registry_enabled_default is False

    asyncio.run(entity.async_set_native_value(0.9))

    assert coordinator.calls[-1] == (0.9, 0.7)


def test_custom_eye_color_saturation_number_maps_state_and_updates_coordinator() -> None:
    coordinator = FakeCoordinator()
    entry = _entry({CONF_ROBOT_NAME: "Vector-ABCD", CONF_HOST: "192.168.1.10"})
    entity = VectorCustomEyeColorSaturationNumber(coordinator, entry)

    assert entity.native_value == 0.7
    assert entity.entity_registry_enabled_default is False

    asyncio.run(entity.async_set_native_value(0.2))

    assert coordinator.calls[-1] == (0.3, 0.2)
