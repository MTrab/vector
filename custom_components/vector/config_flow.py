"""Config flow for Vector integration."""

from __future__ import annotations

import ipaddress
import re
from typing import Any

import voluptuous as vol
from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.const import CONF_HOST, CONF_PASSWORD
from homeassistant.helpers.service_info.dhcp import DhcpServiceInfo
from homeassistant.helpers.service_info.zeroconf import ZeroconfServiceInfo

from .const import CONF_EMAIL, CONF_ROBOT_NAME, CONF_SERIAL, DOMAIN, VECTOR_NAME_PREFIX

VECTOR_HOSTNAME_RE = re.compile(r"^Vector-[A-Za-z0-9]{4,}$", re.IGNORECASE)
HOST_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9.-]{0,252}[A-Za-z0-9]$")

USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_ROBOT_NAME): str,
        vol.Required(CONF_HOST): str,
        vol.Required(CONF_SERIAL): str,
        vol.Optional(CONF_EMAIL): str,
        vol.Optional(CONF_PASSWORD): str,
    }
)


class VectorConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Vector."""

    VERSION = 1

    def _is_valid_host(self, host: str) -> bool:
        """Validate that host is an IP address or hostname."""
        try:
            ipaddress.ip_address(host)
            return True
        except ValueError:
            return bool(HOST_RE.match(host))

    def _discovery_unique_id(self, robot_name: str, host: str) -> str:
        """Return a stable unique ID for a discovered robot."""
        normalized_name = robot_name.lower().strip()
        normalized_host = host.strip()
        return f"{normalized_name}_{normalized_host}"

    async def _async_set_discovery(
        self, robot_name: str, host: str
    ) -> ConfigFlowResult | None:
        """Apply duplicate checks and set flow unique id for discovery."""
        unique_id = self._discovery_unique_id(robot_name, host)
        await self.async_set_unique_id(unique_id)
        self._abort_if_unique_id_configured()

        self.context["title_placeholders"] = {"name": robot_name, "host": host}
        return None

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle the initial user step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            robot_name = user_input[CONF_ROBOT_NAME].strip()
            host = user_input[CONF_HOST].strip()
            serial = user_input.get(CONF_SERIAL, "").strip().lower() or None
            email = user_input.get(CONF_EMAIL, "").strip() or None
            password = user_input.get(CONF_PASSWORD, "").strip() or None

            if not VECTOR_HOSTNAME_RE.match(robot_name):
                errors["base"] = "invalid_robot_name"
            elif not self._is_valid_host(host):
                errors["base"] = "invalid_host"
            elif not serial:
                errors["base"] = "serial_required"
            elif bool(email) != bool(password):
                errors["base"] = "official_credentials_incomplete"

            if not errors:
                unique_host = serial if serial else host
                await self.async_set_unique_id(
                    self._discovery_unique_id(robot_name, unique_host)
                )
                self._abort_if_unique_id_configured()

                data = {
                    CONF_ROBOT_NAME: robot_name,
                    CONF_HOST: host,
                }
                if serial:
                    data[CONF_SERIAL] = serial
                if email:
                    data[CONF_EMAIL] = email
                if password:
                    data[CONF_PASSWORD] = password

                return self.async_create_entry(title=robot_name, data=data)

        return self.async_show_form(
            step_id="user", data_schema=USER_DATA_SCHEMA, errors=errors
        )

    async def async_step_dhcp(
        self, discovery_info: DhcpServiceInfo
    ) -> ConfigFlowResult:
        """Handle DHCP discovery."""
        hostname = (discovery_info.hostname or "").strip()
        ip_address = str(discovery_info.ip)

        if not VECTOR_HOSTNAME_RE.match(hostname):
            return self.async_abort(reason="not_vector")

        await self._async_set_discovery(hostname, ip_address)

        return self.async_create_entry(
            title=hostname,
            data={
                CONF_ROBOT_NAME: hostname,
                CONF_HOST: ip_address,
            },
        )

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

        candidate = name if name.startswith(VECTOR_NAME_PREFIX) else host
        candidate = candidate.strip()

        if not VECTOR_HOSTNAME_RE.match(candidate):
            return self.async_abort(reason="not_vector")

        await self._async_set_discovery(candidate, host or candidate)

        return self.async_create_entry(
            title=candidate,
            data={
                CONF_ROBOT_NAME: candidate,
                CONF_HOST: host or candidate,
            },
        )
