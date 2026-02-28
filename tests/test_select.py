"""Tests for Vector select entities."""

from __future__ import annotations

import asyncio
from types import SimpleNamespace

import pytest

from custom_components.vector.const import (
    CONF_HOST,
    CONF_ROBOT_NAME,
    EYE_COLOR_CUSTOM_OPTION,
)
from custom_components.vector.select import (
    VectorEyeColorPresetSelect,
    VectorMasterVolumeSelect,
)


class FakeCoordinator:
    """Simple coordinator stub for select entity tests."""

    def __init__(self, master_volume: str | None = None) -> None:
        self.master_volume = master_volume
        self.eye_color_preset: str | None = None
        self.eye_color_custom_enabled = False
        self.calls: list[str] = []
        self.eye_calls: list[str] = []

    def async_add_listener(self, update_callback):
        del update_callback
        return lambda: None

    async def async_set_master_volume(self, value: str) -> None:
        self.calls.append(value)
        self.master_volume = value

    async def async_set_eye_color_preset(self, value: str) -> None:
        self.eye_calls.append(value)
        self.eye_color_preset = value


def _entry(data: dict[str, str], entry_id: str = "entry-1") -> SimpleNamespace:
    return SimpleNamespace(data=data, entry_id=entry_id)


def test_master_volume_select_maps_current_option() -> None:
    coordinator = FakeCoordinator(master_volume="medium_low")
    entry = _entry({CONF_ROBOT_NAME: "Vector-ABCD", CONF_HOST: "192.168.1.10"})
    entity = VectorMasterVolumeSelect(coordinator, entry)

    assert entity.current_option == "medium_low"
    assert entity.entity_registry_enabled_default is False


def test_master_volume_select_sets_option_via_coordinator() -> None:
    coordinator = FakeCoordinator(master_volume="low")
    entry = _entry({CONF_ROBOT_NAME: "Vector-ABCD", CONF_HOST: "192.168.1.10"})
    entity = VectorMasterVolumeSelect(coordinator, entry)

    asyncio.run(entity.async_select_option("high"))

    assert coordinator.calls == ["high"]
    assert coordinator.master_volume == "high"


def test_eye_color_select_maps_current_option_and_is_disabled_by_default() -> None:
    coordinator = FakeCoordinator(master_volume="medium_low")
    coordinator.eye_color_preset = "purple"
    entry = _entry({CONF_ROBOT_NAME: "Vector-ABCD", CONF_HOST: "192.168.1.10"})
    entity = VectorEyeColorPresetSelect(coordinator, entry)

    assert entity.current_option == "purple"
    assert entity.options[-1] == EYE_COLOR_CUSTOM_OPTION
    assert entity.entity_registry_enabled_default is False


def test_eye_color_select_maps_custom_state_when_custom_enabled() -> None:
    coordinator = FakeCoordinator(master_volume="medium_low")
    coordinator.eye_color_preset = "purple"
    coordinator.eye_color_custom_enabled = True
    entry = _entry({CONF_ROBOT_NAME: "Vector-ABCD", CONF_HOST: "192.168.1.10"})
    entity = VectorEyeColorPresetSelect(coordinator, entry)

    assert entity.current_option == EYE_COLOR_CUSTOM_OPTION


def test_eye_color_select_sets_option_via_coordinator() -> None:
    coordinator = FakeCoordinator(master_volume="low")
    entry = _entry({CONF_ROBOT_NAME: "Vector-ABCD", CONF_HOST: "192.168.1.10"})
    entity = VectorEyeColorPresetSelect(coordinator, entry)

    asyncio.run(entity.async_select_option("azure_blue"))

    assert coordinator.eye_calls == ["azure_blue"]
    assert coordinator.eye_color_preset == "azure_blue"


def test_eye_color_select_rejects_direct_custom_selection() -> None:
    coordinator = FakeCoordinator(master_volume="low")
    entry = _entry({CONF_ROBOT_NAME: "Vector-ABCD", CONF_HOST: "192.168.1.10"})
    entity = VectorEyeColorPresetSelect(coordinator, entry)

    with pytest.raises(ValueError):
        asyncio.run(entity.async_select_option(EYE_COLOR_CUSTOM_OPTION))
