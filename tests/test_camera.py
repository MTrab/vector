"""Tests for Vector camera entity."""

from __future__ import annotations

import asyncio
from types import SimpleNamespace

from custom_components.vector.camera import VectorNavMapCamera, VectorVisionCamera
from custom_components.vector.const import CONF_HOST, CONF_ROBOT_NAME


class FakeCoordinator:
    """Simple coordinator stub for camera tests."""

    def __init__(self, *, activity: str, frame: bytes | None) -> None:
        self.current_activity = activity
        self._frame = frame
        self._nav_map_frame = frame
        self.start_calls = 0
        self.nav_map_start_calls = 0
        self._nav_map_listener = None

    def async_add_listener(self, update_callback):
        del update_callback
        return lambda: None

    async def async_start_camera_stream(self) -> None:
        self.start_calls += 1

    async def async_get_latest_camera_frame(
        self, *, wait_timeout: float = 1.0
    ) -> bytes | None:
        del wait_timeout
        return self._frame

    async def async_start_nav_map_stream(self) -> None:
        self.nav_map_start_calls += 1

    async def async_get_latest_nav_map_frame(
        self, *, wait_timeout: float = 1.0
    ) -> bytes | None:
        del wait_timeout
        return self._nav_map_frame

    def async_add_nav_map_listener(self, update_callback):
        self._nav_map_listener = update_callback
        return lambda: None


def _entry(data: dict[str, str], entry_id: str = "entry-1") -> SimpleNamespace:
    return SimpleNamespace(data=data, entry_id=entry_id)


def test_camera_entity_disabled_by_default() -> None:
    coordinator = FakeCoordinator(activity="idle", frame=b"\xff\xd8")
    entry = _entry({CONF_ROBOT_NAME: "Vector-ABCD", CONF_HOST: "192.168.1.10"})
    entity = VectorVisionCamera(coordinator, entry)
    assert entity.entity_registry_enabled_default is False


def test_camera_returns_sleep_asset_when_sleeping() -> None:
    coordinator = FakeCoordinator(activity="sleeping", frame=b"\xff\xd8")
    entry = _entry({CONF_ROBOT_NAME: "Vector-ABCD", CONF_HOST: "192.168.1.10"})
    entity = VectorVisionCamera(coordinator, entry)

    image = asyncio.run(entity.async_camera_image())
    assert image is not None
    assert image.startswith(b"\x89PNG")


def test_camera_returns_unknown_asset_when_no_frame() -> None:
    coordinator = FakeCoordinator(activity="idle", frame=None)
    entry = _entry({CONF_ROBOT_NAME: "Vector-ABCD", CONF_HOST: "192.168.1.10"})
    entity = VectorVisionCamera(coordinator, entry)

    image = asyncio.run(entity.async_camera_image())
    assert image is not None
    assert image.startswith(b"\x89PNG")


def test_camera_returns_live_frame_when_available() -> None:
    coordinator = FakeCoordinator(activity="idle", frame=b"\xff\xd8\xff")
    entry = _entry({CONF_ROBOT_NAME: "Vector-ABCD", CONF_HOST: "192.168.1.10"})
    entity = VectorVisionCamera(coordinator, entry)

    image = asyncio.run(entity.async_camera_image())
    assert image == b"\xff\xd8\xff"


def test_nav_map_camera_entity_disabled_by_default() -> None:
    coordinator = FakeCoordinator(activity="idle", frame=b"\x89PNG")
    entry = _entry({CONF_ROBOT_NAME: "Vector-ABCD", CONF_HOST: "192.168.1.10"})
    entity = VectorNavMapCamera(coordinator, entry)
    assert entity.entity_registry_enabled_default is False


def test_nav_map_camera_returns_none_when_no_frame() -> None:
    coordinator = FakeCoordinator(activity="idle", frame=None)
    entry = _entry({CONF_ROBOT_NAME: "Vector-ABCD", CONF_HOST: "192.168.1.10"})
    entity = VectorNavMapCamera(coordinator, entry)

    image = asyncio.run(entity.async_camera_image())
    assert image is None


def test_nav_map_camera_returns_live_frame_when_available() -> None:
    coordinator = FakeCoordinator(activity="idle", frame=b"\x89PNG\r\n\x1a\nframe")
    entry = _entry({CONF_ROBOT_NAME: "Vector-ABCD", CONF_HOST: "192.168.1.10"})
    entity = VectorNavMapCamera(coordinator, entry)

    image = asyncio.run(entity.async_camera_image())
    assert image == b"\x89PNG\r\n\x1a\nframe"
