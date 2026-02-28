"""Tests for Vector domain services."""

from __future__ import annotations

import asyncio
from types import SimpleNamespace

import pytest
from homeassistant.const import ATTR_DEVICE_ID
from homeassistant.exceptions import ServiceValidationError

from custom_components.vector import (
    _async_handle_say_text_service,
    _async_handle_set_eye_color_service,
)
from custom_components.vector.const import (
    ATTR_DURATION_SCALAR,
    ATTR_PITCH_SCALAR,
    ATTR_RGB_COLOR,
    ATTR_TEXT,
    ATTR_USE_VECTOR_VOICE,
    DOMAIN,
)


class FakeCoordinator:
    """Coordinator stub for service tests."""

    def __init__(self) -> None:
        self.calls: list[dict[str, str | bool | float]] = []
        self.eye_color_calls: list[tuple[float, float]] = []

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

    async def async_set_custom_eye_color(
        self,
        *,
        hue: float,
        saturation: float,
    ) -> None:
        self.eye_color_calls.append((hue, saturation))


def _hass_with_coordinators(coordinators: dict[str, FakeCoordinator]) -> SimpleNamespace:
    class FakeDevice:
        def __init__(self, config_entries: set[str]) -> None:
            self.config_entries = config_entries

    class FakeDeviceRegistry:
        def __init__(self) -> None:
            self.devices: dict[str, FakeDevice] = {
                "dev-1": FakeDevice({"entry-1"}),
                "dev-2": FakeDevice({"entry-2"}),
            }

        def async_get(self, device_id: str) -> FakeDevice | None:
            return self.devices.get(device_id)

    return SimpleNamespace(
        data={DOMAIN: {"coordinators": coordinators}},
        _fake_device_registry=FakeDeviceRegistry(),
    )


def test_say_text_service_uses_single_entry_when_no_entry_id() -> None:
    coordinator = FakeCoordinator()
    hass = _hass_with_coordinators({"entry-1": coordinator})

    import custom_components.vector as vector_init

    vector_init.dr.async_get = lambda _hass: _hass._fake_device_registry  # type: ignore[assignment]

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


def test_say_text_service_rejects_missing_device_id_when_multiple_entries() -> None:
    hass = _hass_with_coordinators(
        {"entry-1": FakeCoordinator(), "entry-2": FakeCoordinator()}
    )

    import custom_components.vector as vector_init

    vector_init.dr.async_get = lambda _hass: _hass._fake_device_registry  # type: ignore[assignment]

    with pytest.raises(ServiceValidationError):
        asyncio.run(_async_handle_say_text_service(hass, {ATTR_TEXT: "Hej"}))


def test_say_text_service_rejects_unknown_device_id() -> None:
    hass = _hass_with_coordinators({"entry-1": FakeCoordinator()})

    import custom_components.vector as vector_init

    vector_init.dr.async_get = lambda _hass: _hass._fake_device_registry  # type: ignore[assignment]

    with pytest.raises(ServiceValidationError):
        asyncio.run(
            _async_handle_say_text_service(
                hass,
                {
                    ATTR_DEVICE_ID: "missing",
                    ATTR_TEXT: "Hej",
                },
            )
        )


def test_say_text_service_uses_device_id_for_targeting() -> None:
    coordinator_1 = FakeCoordinator()
    coordinator_2 = FakeCoordinator()
    hass = _hass_with_coordinators({"entry-1": coordinator_1, "entry-2": coordinator_2})

    import custom_components.vector as vector_init

    vector_init.dr.async_get = lambda _hass: _hass._fake_device_registry  # type: ignore[assignment]

    asyncio.run(
        _async_handle_say_text_service(
            hass,
            {
                ATTR_DEVICE_ID: "dev-2",
                ATTR_TEXT: "Hej fra device",
            },
        )
    )

    assert coordinator_1.calls == []
    assert coordinator_2.calls == [
        {
            ATTR_TEXT: "Hej fra device",
            ATTR_USE_VECTOR_VOICE: True,
            ATTR_DURATION_SCALAR: 1.0,
            ATTR_PITCH_SCALAR: 0.0,
        }
    ]


def test_set_eye_color_service_uses_single_entry_when_no_device_id() -> None:
    coordinator = FakeCoordinator()
    hass = _hass_with_coordinators({"entry-1": coordinator})

    import custom_components.vector as vector_init

    vector_init.dr.async_get = lambda _hass: _hass._fake_device_registry  # type: ignore[assignment]

    asyncio.run(
        _async_handle_set_eye_color_service(
            hass,
            {
                ATTR_RGB_COLOR: [255, 0, 0],
            },
        )
    )

    hue, saturation = coordinator.eye_color_calls[-1]
    assert hue == pytest.approx(0.0)
    assert saturation == pytest.approx(1.0)


def test_set_eye_color_service_uses_device_id_for_targeting() -> None:
    coordinator_1 = FakeCoordinator()
    coordinator_2 = FakeCoordinator()
    hass = _hass_with_coordinators({"entry-1": coordinator_1, "entry-2": coordinator_2})

    import custom_components.vector as vector_init

    vector_init.dr.async_get = lambda _hass: _hass._fake_device_registry  # type: ignore[assignment]

    asyncio.run(
        _async_handle_set_eye_color_service(
            hass,
            {
                ATTR_DEVICE_ID: "dev-2",
                ATTR_RGB_COLOR: [0, 0, 255],
            },
        )
    )

    assert coordinator_1.eye_color_calls == []
    hue, saturation = coordinator_2.eye_color_calls[-1]
    assert hue == pytest.approx(2.0 / 3.0)
    assert saturation == pytest.approx(1.0)


def test_set_eye_color_service_rejects_invalid_rgb_shape() -> None:
    coordinator = FakeCoordinator()
    hass = _hass_with_coordinators({"entry-1": coordinator})

    import custom_components.vector as vector_init

    vector_init.dr.async_get = lambda _hass: _hass._fake_device_registry  # type: ignore[assignment]

    with pytest.raises(ServiceValidationError):
        asyncio.run(
            _async_handle_set_eye_color_service(
                hass,
                {
                    ATTR_RGB_COLOR: [255, 255],
                },
            )
        )


def test_set_eye_color_service_accepts_dict_rgb_payload() -> None:
    coordinator = FakeCoordinator()
    hass = _hass_with_coordinators({"entry-1": coordinator})

    import custom_components.vector as vector_init

    vector_init.dr.async_get = lambda _hass: _hass._fake_device_registry  # type: ignore[assignment]

    asyncio.run(
        _async_handle_set_eye_color_service(
            hass,
            {
                ATTR_RGB_COLOR: {"r": 0, "g": 255, "b": 0},
            },
        )
    )

    hue, saturation = coordinator.eye_color_calls[-1]
    assert hue == pytest.approx(1.0 / 3.0)
    assert saturation == pytest.approx(1.0)
