"""Tests for Vector button entities."""

from __future__ import annotations

import asyncio
from types import SimpleNamespace

from custom_components.vector.button import (
    VectorDanceButton,
    VectorExploreStartButton,
    VectorFetchCubeButton,
    VectorGoHomeButton,
    VectorSleepButton,
)
from custom_components.vector.const import CONF_HOST, CONF_ROBOT_NAME


class FakeCoordinator:
    """Simple coordinator stub for button entity tests."""

    def __init__(self) -> None:
        self.calls: list[str] = []

    def async_add_listener(self, update_callback):
        del update_callback
        return lambda: None

    async def async_trigger_quick_action(self, action_key: str) -> None:
        self.calls.append(action_key)


def _entry(data: dict[str, str], entry_id: str = "entry-1") -> SimpleNamespace:
    return SimpleNamespace(data=data, entry_id=entry_id)


def _coordinator_and_entry() -> tuple[FakeCoordinator, SimpleNamespace]:
    coordinator = FakeCoordinator()
    entry = _entry({CONF_ROBOT_NAME: "Vector-ABCD", CONF_HOST: "192.168.1.10"})
    return coordinator, entry


def test_sleep_button_triggers_sleep_action() -> None:
    coordinator, entry = _coordinator_and_entry()
    entity = VectorSleepButton(coordinator, entry)

    asyncio.run(entity.async_press())

    assert coordinator.calls == ["sleep"]


def test_go_home_button_triggers_go_home_action() -> None:
    coordinator, entry = _coordinator_and_entry()
    entity = VectorGoHomeButton(coordinator, entry)

    asyncio.run(entity.async_press())

    assert coordinator.calls == ["go_home"]


def test_explore_start_button_triggers_explore_action() -> None:
    coordinator, entry = _coordinator_and_entry()
    entity = VectorExploreStartButton(coordinator, entry)

    asyncio.run(entity.async_press())

    assert coordinator.calls == ["explore_start"]


def test_dance_button_triggers_dance_action() -> None:
    coordinator, entry = _coordinator_and_entry()
    entity = VectorDanceButton(coordinator, entry)

    asyncio.run(entity.async_press())

    assert coordinator.calls == ["dance"]


def test_fetch_cube_button_triggers_fetch_cube_action() -> None:
    coordinator, entry = _coordinator_and_entry()
    entity = VectorFetchCubeButton(coordinator, entry)

    asyncio.run(entity.async_press())

    assert coordinator.calls == ["fetch_cube"]
