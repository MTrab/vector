"""Tests for Vector config flow."""

from __future__ import annotations

import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

from homeassistant.const import CONF_HOST, CONF_PASSWORD

from custom_components.vector.config_flow import VectorConfigFlow
from custom_components.vector.const import CONF_EMAIL, CONF_ROBOT_NAME, CONF_SERIAL


def _user_input(**overrides: str) -> dict[str, str]:
    data = {
        CONF_ROBOT_NAME: "Vector-ABCD",
        CONF_HOST: "192.168.1.10",
        CONF_SERIAL: "00A1",
        CONF_EMAIL: "",
        CONF_PASSWORD: "",
    }
    data.update(overrides)
    return data


def _prepare_flow(flow: VectorConfigFlow) -> None:
    flow.async_set_unique_id = AsyncMock()  # type: ignore[method-assign]
    flow._abort_if_unique_id_configured = Mock()  # type: ignore[method-assign]


def test_async_step_user_invalid_robot_name() -> None:
    flow = VectorConfigFlow()

    result = asyncio.run(
        flow.async_step_user(_user_input(**{CONF_ROBOT_NAME: "NotVector"}))
    )

    assert result["type"] == "form"
    assert result["errors"]["base"] == "invalid_robot_name"


def test_async_step_user_invalid_host() -> None:
    flow = VectorConfigFlow()

    result = asyncio.run(flow.async_step_user(_user_input(**{CONF_HOST: "bad host"})))

    assert result["type"] == "form"
    assert result["errors"]["base"] == "invalid_host"


def test_async_step_user_rejects_incomplete_credentials() -> None:
    flow = VectorConfigFlow()

    result = asyncio.run(
        flow.async_step_user(_user_input(**{CONF_EMAIL: "user@example.com"}))
    )

    assert result["type"] == "form"
    assert result["errors"]["base"] == "official_credentials_incomplete"


def test_async_step_user_creates_entry_and_normalizes_serial() -> None:
    flow = VectorConfigFlow()
    _prepare_flow(flow)

    result = asyncio.run(flow.async_step_user(_user_input()))

    assert result["type"] == "create_entry"
    assert result["title"] == "Vector-ABCD"
    assert result["data"][CONF_SERIAL] == "00a1"
    flow.async_set_unique_id.assert_awaited_once_with("vector-abcd_00a1")
    flow._abort_if_unique_id_configured.assert_called_once()


def test_async_step_dhcp_aborts_for_non_vector_hostname() -> None:
    flow = VectorConfigFlow()

    result = asyncio.run(
        flow.async_step_dhcp(SimpleNamespace(hostname="printer", ip="192.168.1.15"))
    )

    assert result["type"] == "abort"
    assert result["reason"] == "not_vector"


def test_async_step_zeroconf_creates_entry_for_vector_name() -> None:
    flow = VectorConfigFlow()
    _prepare_flow(flow)

    result = asyncio.run(
        flow.async_step_zeroconf(
            SimpleNamespace(
                name="Vector-ABCD._tcp.local.",
                host="vector-abcd.local.",
            )
        )
    )

    assert result["type"] == "create_entry"
    assert result["title"] == "Vector-ABCD"
    assert result["data"][CONF_ROBOT_NAME] == "Vector-ABCD"
    assert result["data"][CONF_HOST] == "vector-abcd.local"
    flow.async_set_unique_id.assert_awaited_once_with("vector-abcd_vector-abcd.local")
    flow._abort_if_unique_id_configured.assert_called_once()
