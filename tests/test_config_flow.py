"""Tests for Vector config flow."""

from __future__ import annotations

import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import pytest
from homeassistant.const import CONF_HOST, CONF_PASSWORD
from homeassistant.data_entry_flow import AbortFlow

from custom_components.vector.config_flow import VectorConfigFlow, VectorOptionsFlow
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


def _prepare_flow(flow: VectorConfigFlow, *entries: SimpleNamespace) -> None:
    flow.async_set_unique_id = AsyncMock()  # type: ignore[method-assign]
    flow._abort_if_unique_id_configured = Mock()  # type: ignore[method-assign]
    flow._async_current_entries = Mock(return_value=entries)  # type: ignore[method-assign]


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
    flow.async_set_unique_id.assert_awaited_once_with("vector-abcd")
    flow._abort_if_unique_id_configured.assert_called_once()


def test_async_step_user_creates_entry_without_serial() -> None:
    flow = VectorConfigFlow()
    _prepare_flow(flow)

    result = asyncio.run(flow.async_step_user(_user_input(**{CONF_SERIAL: ""})))

    assert result["type"] == "create_entry"
    assert result["title"] == "Vector-ABCD"
    assert CONF_SERIAL not in result["data"]
    flow.async_set_unique_id.assert_awaited_once_with("vector-abcd")
    flow._abort_if_unique_id_configured.assert_called_once()


def test_async_step_dhcp_aborts_for_non_vector_hostname() -> None:
    flow = VectorConfigFlow()

    result = asyncio.run(
        flow.async_step_dhcp(SimpleNamespace(hostname="printer", ip="192.168.1.15"))
    )

    assert result["type"] == "abort"
    assert result["reason"] == "not_vector"


@pytest.mark.parametrize(
    ("step", "discovery"),
    [
        ("async_step_dhcp", SimpleNamespace(hostname="vector-abcd", ip="192.168.1.99")),
        (
            "async_step_zeroconf",
            SimpleNamespace(name="Vector-ABCD._tcp.local.", host="vector-abcd.local."),
        ),
    ],
)
def test_discovery_aborts_for_legacy_manual_entry(step, discovery) -> None:
    entry = SimpleNamespace(
        unique_id="vector-abcd_00a1",
        data=_user_input(),
    )
    flow = VectorConfigFlow()
    _prepare_flow(flow, entry)

    with pytest.raises(AbortFlow, match="already_configured"):
        asyncio.run(getattr(flow, step)(discovery))

    flow.async_set_unique_id.assert_awaited_once_with("vector-abcd")
    assert entry.data[CONF_HOST] == "192.168.1.10"


def test_discovery_honors_legacy_ignored_entry() -> None:
    flow = VectorConfigFlow()
    _prepare_flow(flow, SimpleNamespace(unique_id="vector-abcd_192.168.1.10", data={}))

    with pytest.raises(AbortFlow, match="already_configured"):
        asyncio.run(
            flow.async_step_dhcp(
                SimpleNamespace(hostname="Vector-ABCD", ip="192.168.1.99")
            )
        )


def test_reconfigure_updates_unique_id_when_robot_name_changes() -> None:
    entry = SimpleNamespace(unique_id="vector-abcd", data=_user_input())
    flow = VectorConfigFlow()
    _prepare_flow(flow, entry)
    flow._get_reconfigure_entry = Mock(return_value=entry)
    flow.async_update_reload_and_abort = Mock()

    asyncio.run(
        flow.async_step_reconfigure(_user_input(**{CONF_ROBOT_NAME: "Vector-9876"}))
    )

    flow.async_set_unique_id.assert_awaited_once_with("vector-9876")
    flow.async_update_reload_and_abort.assert_called_once_with(
        entry,
        unique_id="vector-9876",
        data_updates={
            CONF_ROBOT_NAME: "Vector-9876",
            CONF_HOST: "192.168.1.10",
            CONF_SERIAL: "00a1",
        },
    )


def test_async_step_zeroconf_requires_confirmation_for_vector_name() -> None:
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

    assert result["type"] == "form"
    assert result["step_id"] == "discovery_confirm"
    flow.async_set_unique_id.assert_awaited_once_with("vector-abcd")
    flow._abort_if_unique_id_configured.assert_called_once()

    confirm_result = asyncio.run(flow.async_step_discovery_confirm({}))
    assert confirm_result["type"] == "form"
    assert confirm_result["step_id"] == "discovery_setup"

    setup_result = asyncio.run(
        flow.async_step_discovery_setup(_user_input(**{CONF_HOST: "vector-abcd.local"}))
    )
    assert setup_result["type"] == "create_entry"
    assert setup_result["title"] == "Vector-ABCD"
    assert setup_result["data"][CONF_ROBOT_NAME] == "Vector-ABCD"
    assert setup_result["data"][CONF_HOST] == "vector-abcd.local"
    assert setup_result["data"][CONF_SERIAL] == "00a1"
    assert flow.async_set_unique_id.await_count == 2
    flow.async_set_unique_id.assert_awaited_with("vector-abcd")


def test_discovery_setup_without_serial_uses_robot_name_in_unique_id() -> None:
    flow = VectorConfigFlow()
    _prepare_flow(flow)

    _ = asyncio.run(
        flow.async_step_zeroconf(
            SimpleNamespace(
                name="Vector-ABCD._tcp.local.",
                host="vector-abcd.local.",
            )
        )
    )
    _ = asyncio.run(flow.async_step_discovery_confirm({}))

    setup_result = asyncio.run(
        flow.async_step_discovery_setup(
            _user_input(**{CONF_HOST: "vector-abcd.local", CONF_SERIAL: ""})
        )
    )

    assert setup_result["type"] == "create_entry"
    assert CONF_SERIAL not in setup_result["data"]
    flow.async_set_unique_id.assert_awaited_with("vector-abcd")


def test_discovery_setup_rejects_incomplete_credentials() -> None:
    flow = VectorConfigFlow()
    _prepare_flow(flow)

    _ = asyncio.run(
        flow.async_step_zeroconf(
            SimpleNamespace(
                name="Vector-ABCD._tcp.local.",
                host="vector-abcd.local.",
            )
        )
    )
    _ = asyncio.run(flow.async_step_discovery_confirm({}))

    setup_result = asyncio.run(
        flow.async_step_discovery_setup(
            _user_input(
                **{
                    CONF_HOST: "vector-abcd.local",
                    CONF_EMAIL: "user@example.com",
                    CONF_PASSWORD: "",
                }
            )
        )
    )

    assert setup_result["type"] == "form"
    assert setup_result["step_id"] == "discovery_setup"
    assert setup_result["errors"]["base"] == "official_credentials_incomplete"


def test_async_step_zeroconf_requires_confirmation_for_lowercase_vector_name() -> None:
    flow = VectorConfigFlow()
    _prepare_flow(flow)

    result = asyncio.run(
        flow.async_step_zeroconf(
            SimpleNamespace(
                name="vector-abcd._tcp.local.",
                host="vector-abcd.local.",
            )
        )
    )

    assert result["type"] == "form"
    assert result["step_id"] == "discovery_confirm"
    flow.async_set_unique_id.assert_awaited_once_with("vector-abcd")
    flow._abort_if_unique_id_configured.assert_called_once()

    confirm_result = asyncio.run(flow.async_step_discovery_confirm({}))
    assert confirm_result["type"] == "form"
    assert confirm_result["step_id"] == "discovery_setup"

    setup_result = asyncio.run(
        flow.async_step_discovery_setup(
            _user_input(
                **{
                    CONF_ROBOT_NAME: "vector-abcd",
                    CONF_HOST: "vector-abcd.local",
                }
            )
        )
    )
    assert setup_result["type"] == "create_entry"
    assert setup_result["title"] == "vector-abcd"
    assert setup_result["data"][CONF_ROBOT_NAME] == "vector-abcd"
    assert setup_result["data"][CONF_HOST] == "vector-abcd.local"


def test_async_step_dhcp_requires_confirmation_for_vector_hostname() -> None:
    flow = VectorConfigFlow()
    _prepare_flow(flow)

    result = asyncio.run(
        flow.async_step_dhcp(SimpleNamespace(hostname="Vector-A9E9", ip="192.168.1.16"))
    )

    assert result["type"] == "form"
    assert result["step_id"] == "discovery_confirm"
    flow.async_set_unique_id.assert_awaited_once_with("vector-a9e9")
    flow._abort_if_unique_id_configured.assert_called_once()

    confirm_result = asyncio.run(flow.async_step_discovery_confirm({}))
    assert confirm_result["type"] == "form"
    assert confirm_result["step_id"] == "discovery_setup"

    setup_result = asyncio.run(
        flow.async_step_discovery_setup(
            _user_input(
                **{
                    CONF_ROBOT_NAME: "Vector-A9E9",
                    CONF_HOST: "192.168.1.16",
                }
            )
        )
    )
    assert setup_result["type"] == "create_entry"
    assert setup_result["title"] == "Vector-A9E9"
    assert setup_result["data"][CONF_ROBOT_NAME] == "Vector-A9E9"
    assert setup_result["data"][CONF_HOST] == "192.168.1.16"


def test_options_flow_creates_options_and_normalizes_serial() -> None:
    entry = SimpleNamespace(
        entry_id="entry-1",
        data=_user_input(),
        options={},
        title="Vector-ABCD",
    )
    flow = VectorOptionsFlow()
    flow.hass = SimpleNamespace(
        config_entries=SimpleNamespace(async_get_known_entry=lambda _entry_id: entry)
    )
    flow.handler = entry.entry_id

    result = asyncio.run(
        flow.async_step_init(
            _user_input(
                **{
                    CONF_HOST: "vector-abcd.local",
                    CONF_SERIAL: "00B2",
                }
            )
        )
    )

    assert result["type"] == "create_entry"
    assert result["data"][CONF_HOST] == "vector-abcd.local"
    assert result["data"][CONF_SERIAL] == "00b2"


def test_options_flow_rejects_incomplete_credentials() -> None:
    entry = SimpleNamespace(
        entry_id="entry-1",
        data=_user_input(),
        options={},
        title="Vector-ABCD",
    )
    flow = VectorOptionsFlow()
    flow.hass = SimpleNamespace(
        config_entries=SimpleNamespace(async_get_known_entry=lambda _entry_id: entry)
    )
    flow.handler = entry.entry_id

    result = asyncio.run(
        flow.async_step_init(
            _user_input(
                **{
                    CONF_EMAIL: "user@example.com",
                    CONF_PASSWORD: "",
                }
            )
        )
    )

    assert result["type"] == "form"
    assert result["errors"]["base"] == "official_credentials_incomplete"


def test_options_flow_hides_credentials_when_not_preconfigured() -> None:
    entry = SimpleNamespace(
        entry_id="entry-1",
        data={
            CONF_ROBOT_NAME: "Vector-ABCD",
            CONF_HOST: "192.168.1.10",
        },
        options={},
        title="Vector-ABCD",
    )
    flow = VectorOptionsFlow()
    flow.hass = SimpleNamespace(
        config_entries=SimpleNamespace(async_get_known_entry=lambda _entry_id: entry)
    )
    flow.handler = entry.entry_id

    result = asyncio.run(flow.async_step_init())
    schema = result["data_schema"].schema
    field_names = {
        key.schema
        for key in schema
        if hasattr(key, "schema") and isinstance(key.schema, str)
    }

    assert CONF_HOST in field_names
    assert CONF_SERIAL in field_names
    assert CONF_EMAIL not in field_names
    assert CONF_PASSWORD not in field_names


def test_options_flow_shows_credentials_when_preconfigured() -> None:
    entry = SimpleNamespace(
        entry_id="entry-1",
        data={
            CONF_ROBOT_NAME: "Vector-ABCD",
            CONF_HOST: "192.168.1.10",
            CONF_EMAIL: "user@example.com",
            CONF_PASSWORD: "secret",
        },
        options={},
        title="Vector-ABCD",
    )
    flow = VectorOptionsFlow()
    flow.hass = SimpleNamespace(
        config_entries=SimpleNamespace(async_get_known_entry=lambda _entry_id: entry)
    )
    flow.handler = entry.entry_id

    result = asyncio.run(flow.async_step_init())
    schema = result["data_schema"].schema
    field_names = {
        key.schema
        for key in schema
        if hasattr(key, "schema") and isinstance(key.schema, str)
    }

    assert CONF_HOST in field_names
    assert CONF_SERIAL in field_names
    assert CONF_EMAIL in field_names
    assert CONF_PASSWORD in field_names
