"""Config flow for Vector integration."""

from __future__ import annotations

import ipaddress
import re
from typing import Any

import voluptuous as vol
from homeassistant.config_entries import ConfigEntry, ConfigFlow, ConfigFlowResult, OptionsFlow
from homeassistant.const import CONF_HOST, CONF_PASSWORD
from homeassistant.data_entry_flow import AbortFlow
from homeassistant.helpers.service_info.dhcp import DhcpServiceInfo
from homeassistant.helpers.service_info.zeroconf import ZeroconfServiceInfo

from .const import CONF_EMAIL, CONF_ROBOT_NAME, CONF_SERIAL, DOMAIN

VECTOR_HOSTNAME_RE = re.compile(r"^Vector-[A-Za-z0-9]{4,}$", re.IGNORECASE)
HOST_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9.-]{0,252}[A-Za-z0-9]$")

USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_ROBOT_NAME): str,
        vol.Required(CONF_HOST): str,
        vol.Optional(CONF_SERIAL): str,
        vol.Optional(CONF_EMAIL): str,
        vol.Optional(CONF_PASSWORD): str,
    }
)


class VectorConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Vector."""

    VERSION = 1

    def __init__(self) -> None:
        """Initialize config flow."""
        self._discovered_data: dict[str, str] | None = None

    @staticmethod
    def async_get_options_flow(config_entry: ConfigEntry) -> OptionsFlow:
        """Return options flow."""
        del config_entry
        return VectorOptionsFlow()

    def _is_valid_host(self, host: str) -> bool:
        """Validate that host is an IP address or hostname."""
        try:
            ipaddress.ip_address(host)
            return True
        except ValueError:
            return bool(HOST_RE.match(host))

    async def _async_set_robot_identity(
        self, robot_name: str, *, reconfigure_entry: ConfigEntry | None = None
    ) -> str:
        """Reserve the robot name and check entries with legacy IDs."""
        unique_id = robot_name.strip().lower()
        await self.async_set_unique_id(unique_id)
        if reconfigure_entry is None:
            self._abort_if_unique_id_configured()

        for entry in self._async_current_entries():
            if entry is reconfigure_entry:
                continue
            # Ignored discovery entries may only have the original unique ID.
            entry_name = (
                entry.data.get(CONF_ROBOT_NAME)
                or (entry.unique_id or "").partition("_")[0]
            )
            if unique_id == entry_name.strip().lower() or unique_id == entry.unique_id:
                raise AbortFlow("already_configured")
        return unique_id

    def _normalize_form_data(
        self, user_input: dict[str, Any]
    ) -> tuple[dict[str, str | None], dict[str, str]]:
        """Normalize config flow form data and return validation errors."""
        robot_name = user_input[CONF_ROBOT_NAME].strip()
        host = user_input[CONF_HOST].strip()
        serial = user_input.get(CONF_SERIAL, "").strip().lower() or None
        email = user_input.get(CONF_EMAIL, "").strip() or None
        password = user_input.get(CONF_PASSWORD, "").strip() or None

        errors: dict[str, str] = {}
        if not VECTOR_HOSTNAME_RE.match(robot_name):
            errors["base"] = "invalid_robot_name"
        elif not self._is_valid_host(host):
            errors["base"] = "invalid_host"
        elif bool(email) != bool(password):
            errors["base"] = "official_credentials_incomplete"

        return {
            CONF_ROBOT_NAME: robot_name,
            CONF_HOST: host,
            CONF_SERIAL: serial,
            CONF_EMAIL: email,
            CONF_PASSWORD: password,
        }, errors

    def _entry_data_from_normalized(
        self, normalized: dict[str, str | None]
    ) -> dict[str, str]:
        """Build config entry payload from normalized values."""
        data: dict[str, str] = {
            CONF_ROBOT_NAME: normalized[CONF_ROBOT_NAME] or "",
            CONF_HOST: normalized[CONF_HOST] or "",
        }
        if normalized[CONF_SERIAL]:
            data[CONF_SERIAL] = normalized[CONF_SERIAL]
        if normalized[CONF_EMAIL]:
            data[CONF_EMAIL] = normalized[CONF_EMAIL]
        if normalized[CONF_PASSWORD]:
            data[CONF_PASSWORD] = normalized[CONF_PASSWORD]
        return data

    async def _async_start_discovery(
        self, robot_name: str, host: str
    ) -> ConfigFlowResult:
        """Start a user-confirmed discovery flow."""
        await self._async_set_robot_identity(robot_name)
        try:
            self.context["title_placeholders"] = {"robot_name": robot_name}
        except TypeError:
            # Some test harnesses expose context as read-only mappingproxy.
            pass
        self._discovered_data = {
            CONF_ROBOT_NAME: robot_name,
            CONF_HOST: host,
        }
        return await self.async_step_discovery_confirm()

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle the initial user step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            normalized, errors = self._normalize_form_data(user_input)

            if not errors:
                await self._async_set_robot_identity(normalized[CONF_ROBOT_NAME] or "")
                return self.async_create_entry(
                    title=normalized[CONF_ROBOT_NAME] or "",
                    data=self._entry_data_from_normalized(normalized),
                )

        return self.async_show_form(
            step_id="user", data_schema=USER_DATA_SCHEMA, errors=errors
        )

    async def async_step_reconfigure(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle reconfiguration of an existing config entry."""
        reconfigure_entry = self._get_reconfigure_entry()
        errors: dict[str, str] = {}

        if user_input is not None:
            normalized, errors = self._normalize_form_data(user_input)
            if not errors:
                data = self._entry_data_from_normalized(normalized)
                if (
                    data[CONF_ROBOT_NAME].lower()
                    != reconfigure_entry.data[CONF_ROBOT_NAME].lower()
                ):
                    unique_id = await self._async_set_robot_identity(
                        data[CONF_ROBOT_NAME], reconfigure_entry=reconfigure_entry
                    )
                    return self.async_update_reload_and_abort(
                        reconfigure_entry, unique_id=unique_id, data_updates=data
                    )
                return self.async_update_reload_and_abort(
                    reconfigure_entry,
                    data_updates=data,
                )

        return self.async_show_form(
            step_id="reconfigure",
            data_schema=self.add_suggested_values_to_schema(
                USER_DATA_SCHEMA, reconfigure_entry.data
            ),
            errors=errors,
        )

    async def async_step_discovery_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Confirm discovered robot before showing setup fields."""
        if self._discovered_data is None:
            return self.async_abort(reason="not_vector")

        if user_input is not None:
            return await self.async_step_discovery_setup()

        return self.async_show_form(
            step_id="discovery_confirm",
            data_schema=vol.Schema({}),
            description_placeholders={
                "robot_name": self._discovered_data[CONF_ROBOT_NAME],
                "host": self._discovered_data[CONF_HOST],
            },
        )

    async def async_step_discovery_setup(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Show editable setup form after discovery confirmation."""
        if self._discovered_data is None:
            return self.async_abort(reason="not_vector")

        errors: dict[str, str] = {}
        if user_input is not None:
            normalized, errors = self._normalize_form_data(user_input)
            if not errors:
                await self._async_set_robot_identity(normalized[CONF_ROBOT_NAME] or "")
                self._discovered_data = None
                return self.async_create_entry(
                    title=normalized[CONF_ROBOT_NAME] or "",
                    data=self._entry_data_from_normalized(normalized),
                )

        suggested_values = dict(self._discovered_data)
        if user_input is not None:
            suggested_values.update(user_input)
        return self.async_show_form(
            step_id="discovery_setup",
            data_schema=self.add_suggested_values_to_schema(
                USER_DATA_SCHEMA,
                suggested_values,
            ),
            errors=errors,
        )

    async def async_step_dhcp(
        self, discovery_info: DhcpServiceInfo
    ) -> ConfigFlowResult:
        """Handle DHCP discovery."""
        hostname = (discovery_info.hostname or "").strip()
        ip_address = str(discovery_info.ip)

        if not VECTOR_HOSTNAME_RE.match(hostname):
            return self.async_abort(reason="not_vector")

        return await self._async_start_discovery(hostname, ip_address)

    async def async_step_zeroconf(
        self, discovery_info: ZeroconfServiceInfo
    ) -> ConfigFlowResult:
        """Handle Zeroconf discovery."""
        name = (discovery_info.name or "").strip()
        host = (discovery_info.host or "").strip()

        # mDNS names often include trailing dots and service suffixes.
        if name.endswith(".local."):
            name = name[:-7]
        if "." in name:
            name = name.split(".", 1)[0]
        if host.endswith("."):
            host = host[:-1]

        candidate = name.strip()
        if not VECTOR_HOSTNAME_RE.match(candidate):
            candidate = host.split(".", 1)[0].strip()

        if not VECTOR_HOSTNAME_RE.match(candidate):
            return self.async_abort(reason="not_vector")

        return await self._async_start_discovery(candidate, host or candidate)


class VectorOptionsFlow(OptionsFlow):
    """Handle Vector options."""

    def _is_valid_host(self, host: str) -> bool:
        """Validate that host is an IP address or hostname."""
        try:
            ipaddress.ip_address(host)
            return True
        except ValueError:
            return bool(HOST_RE.match(host))

    def _normalize_form_data(
        self, user_input: dict[str, Any]
    ) -> tuple[dict[str, str | None], dict[str, str]]:
        """Normalize options data and return validation errors."""
        host = user_input[CONF_HOST].strip()
        serial = user_input.get(CONF_SERIAL, "").strip().lower() or None
        email = user_input.get(CONF_EMAIL, "").strip() or None
        password = user_input.get(CONF_PASSWORD, "").strip() or None

        errors: dict[str, str] = {}
        if not self._is_valid_host(host):
            errors["base"] = "invalid_host"
        elif bool(email) != bool(password):
            errors["base"] = "official_credentials_incomplete"

        return {
            CONF_HOST: host,
            CONF_SERIAL: serial,
            CONF_EMAIL: email,
            CONF_PASSWORD: password,
        }, errors

    def _options_from_normalized(
        self, normalized: dict[str, str | None]
    ) -> dict[str, str]:
        """Build options payload from normalized values."""
        options: dict[str, str] = {
            CONF_HOST: normalized[CONF_HOST] or "",
        }
        if normalized[CONF_SERIAL]:
            options[CONF_SERIAL] = normalized[CONF_SERIAL]
        if normalized[CONF_EMAIL]:
            options[CONF_EMAIL] = normalized[CONF_EMAIL]
        if normalized[CONF_PASSWORD]:
            options[CONF_PASSWORD] = normalized[CONF_PASSWORD]
        return options

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Manage Vector options."""
        errors: dict[str, str] = {}
        combined_values = {**self.config_entry.data, **self.config_entry.options}
        has_credentials = bool(combined_values.get(CONF_EMAIL)) and bool(
            combined_values.get(CONF_PASSWORD)
        )
        options_schema_dict: dict[Any, Any] = {
            vol.Required(CONF_HOST): str,
            vol.Optional(CONF_SERIAL): str,
        }
        if has_credentials:
            options_schema_dict[vol.Optional(CONF_EMAIL)] = str
            options_schema_dict[vol.Optional(CONF_PASSWORD)] = str
        options_schema = vol.Schema(options_schema_dict)

        if user_input is not None:
            normalized, errors = self._normalize_form_data(user_input)
            if not errors:
                return self.async_create_entry(
                    title="",
                    data=self._options_from_normalized(normalized),
                )

        return self.async_show_form(
            step_id="init",
            data_schema=self.add_suggested_values_to_schema(
                options_schema,
                combined_values,
            ),
            errors=errors,
        )
