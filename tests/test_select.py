"""Tests for Vector select entities."""

from __future__ import annotations

import asyncio
from types import SimpleNamespace

from custom_components.vector.const import CONF_HOST, CONF_ROBOT_NAME
from custom_components.vector.select import VectorMasterVolumeSelect


class FakeCoordinator:
    """Simple coordinator stub for select entity tests."""

    def __init__(self, master_volume: str | None = None) -> None:
        self.master_volume = master_volume
        self.calls: list[str] = []

    def async_add_listener(self, update_callback):
        del update_callback
        return lambda: None

    async def async_set_master_volume(self, value: str) -> None:
        self.calls.append(value)
        self.master_volume = value


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
