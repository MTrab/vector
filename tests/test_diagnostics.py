"""Tests for Vector diagnostics."""

from __future__ import annotations

import asyncio
from types import SimpleNamespace

from homeassistant.const import CONF_HOST, CONF_PASSWORD

from custom_components.vector.const import CONF_EMAIL, CONF_SERIAL, DOMAIN
from custom_components.vector.diagnostics import async_get_config_entry_diagnostics


def test_async_get_config_entry_diagnostics_redacts_sensitive_values() -> None:
    """Diagnostics output should redact sensitive config entry fields."""
    coordinator = SimpleNamespace(
        current_activity="idle",
        battery_percent=66,
        battery_level="nominal",
        is_charging=False,
        firmware_version="2.1.3",
        master_volume="medium",
        stimulation_value=0.5,
    )
    entry = SimpleNamespace(
        entry_id="entry-1",
        data={
            "robot_name": "Vector-ABCD",
            CONF_HOST: "192.168.1.10",
            CONF_SERIAL: "00a1",
            CONF_EMAIL: "user@example.com",
            CONF_PASSWORD: "secret",
        },
    )
    hass = SimpleNamespace(
        data={
            DOMAIN: {
                entry.entry_id: {
                    "coordinator": coordinator,
                }
            }
        }
    )

    diagnostics = asyncio.run(async_get_config_entry_diagnostics(hass, entry))

    assert diagnostics["entry"]["robot_name"] == "Vector-ABCD"
    assert diagnostics["entry"][CONF_HOST] == "**REDACTED**"
    assert diagnostics["entry"][CONF_SERIAL] == "**REDACTED**"
    assert diagnostics["entry"][CONF_EMAIL] == "**REDACTED**"
    assert diagnostics["entry"][CONF_PASSWORD] == "**REDACTED**"
    assert diagnostics["coordinator"]["current_activity"] == "idle"
