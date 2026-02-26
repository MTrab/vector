"""Tests for Vector integration setup/unload."""

from __future__ import annotations

import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from homeassistant.exceptions import ConfigEntryNotReady

import custom_components.vector as vector_init
from custom_components.vector.const import DOMAIN


class FakeCoordinator:
    """Coordinator test double for setup flow tests."""

    def __init__(self, hass, entry) -> None:  # type: ignore[no-untyped-def]
        del hass, entry
        self.async_validate_connection = AsyncMock()
        self.async_shutdown = AsyncMock()

    async def async_start_runtime(self) -> None:
        return None


def _hass() -> SimpleNamespace:
    """Create minimal hass stub for setup/unload tests."""

    def _create_background_task(coro, name: str):  # type: ignore[no-untyped-def]
        del name
        coro.close()
        return object()

    return SimpleNamespace(
        data={},
        config_entries=SimpleNamespace(
            async_forward_entry_setups=AsyncMock(),
            async_unload_platforms=AsyncMock(return_value=True),
        ),
        async_create_background_task=_create_background_task,
    )


def _entry(entry_id: str = "entry-1") -> SimpleNamespace:
    return SimpleNamespace(entry_id=entry_id, data={"robot_name": "Vector-ABCD"})


def test_async_setup_entry_success(monkeypatch: pytest.MonkeyPatch) -> None:
    hass = _hass()
    entry = _entry()
    monkeypatch.setattr(vector_init, "VectorCoordinator", FakeCoordinator)

    result = asyncio.run(vector_init.async_setup_entry(hass, entry))

    assert result is True
    assert entry.entry_id in hass.data[DOMAIN]
    hass.config_entries.async_forward_entry_setups.assert_awaited_once()


def test_async_setup_entry_raises_not_ready_on_validation_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    hass = _hass()
    entry = _entry()

    class FailingCoordinator(FakeCoordinator):
        def __init__(self, hass, entry) -> None:  # type: ignore[no-untyped-def]
            super().__init__(hass, entry)
            self.async_validate_connection = AsyncMock(
                side_effect=RuntimeError("Authentication failed for robot RPC call")
            )

    monkeypatch.setattr(vector_init, "VectorCoordinator", FailingCoordinator)

    with pytest.raises(ConfigEntryNotReady):
        asyncio.run(vector_init.async_setup_entry(hass, entry))

    assert entry.entry_id not in hass.data.get(DOMAIN, {})
    hass.config_entries.async_forward_entry_setups.assert_not_called()
