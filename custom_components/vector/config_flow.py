"""Digital Dream Labs Vector integration config flow."""

from __future__ import annotations

import logging

import ha_vector
import voluptuous as vol
from bleak import discover
from homeassistant.config_entries import (
    CONN_CLASS_LOCAL_PUSH,
    ConfigFlow,
    ConfigFlowResult,
)
from homeassistant.const import CONF_EMAIL, CONF_NAME, CONF_PASSWORD
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.service_info.dhcp import DhcpServiceInfo

from .const import (
    CONF_CERTIFICATE,
    CONF_ESCAPEPOD,
    CONF_GUID,
    CONF_IP,
    CONF_SERIAL,
    DOMAIN,
)
from .helpers import VectorStore
from .vector_setup import VectorSetup

_LOGGER = logging.getLogger(__name__)

DATA_SCHEME = vol.Schema(
    {
        vol.Optional(CONF_EMAIL): str,
        vol.Optional(CONF_PASSWORD): str,
        vol.Required(CONF_ESCAPEPOD, default=True): bool,
        vol.Required(CONF_NAME): str,
        vol.Required(CONF_SERIAL): str,
        vol.Required(CONF_IP): str,
    }
)


class MissingEmailOrPassword(Exception):
    """Raised when missing email or password if not using Escapepod."""


async def validate_input(hass: HomeAssistant, data: dict) -> bool:
    """Validate the user input allows us to connect.
    Data has the keys from DATA_SCHEMA with values provided by the user.
    """
    if not data[CONF_ESCAPEPOD]:
        if not CONF_EMAIL in data or not CONF_PASSWORD in data:
            raise MissingEmailOrPassword()

    if not "vector-" in data[CONF_NAME].lower():
        data[CONF_NAME] = f"Vector-{data[CONF_NAME]}"

    store = VectorStore(hass, data[CONF_NAME])
    await store.async_load()
    vector_api = VectorSetup(
        email=data[CONF_EMAIL] if CONF_EMAIL in data else None,
        password=data[CONF_PASSWORD] if CONF_PASSWORD in data else None,
        name=data[CONF_NAME],
        serial=data[CONF_SERIAL],
        ipaddress=data[CONF_IP],
        escapepod=data[CONF_ESCAPEPOD],
        cert_path=store.cert_path,
        client=async_get_clientsession(hass),
    )

    await vector_api.async_configure()

    config = {
        CONF_CERTIFICATE: vector_api.certificate,
        CONF_NAME: data[CONF_NAME],
        CONF_GUID: vector_api.guid.replace("b'", "").replace("'", ""),
    }

    await store.async_save(config)

    return True


class VectorRobotConfigFlow(ConfigFlow, domain=DOMAIN):
    """Config flow handler for Vector Robot integration."""

    VERSION = 1
    CONNECTION_CLASS = CONN_CLASS_LOCAL_PUSH

    def check_for_existing(self, data):
        """Check whether an existing entry is using the same settings."""
        return any(
            entry.data.get(CONF_SERIAL) == data.get(CONF_SERIAL)
            for entry in self._async_current_entries()
        )

    def __init__(self):
        """Initialize the config flow."""
        self._errors = {}
        self._escapepod = False

    async def async_step_user(self, user_input=None):
        """Handle the initial Clever integration step."""
        self._errors = {}

        if user_input is not None:
            if self.check_for_existing(user_input):
                return self.async_abort(reason="already_exists")

            try:
                validated = await validate_input(self.hass, user_input)
            except MissingEmailOrPassword:
                _LOGGER.error(
                    "No email or password was specified and you specified not using Escapepod!"
                )
                self._errors["base"] = "missing_email_or_password"
            except Exception as exc:  # pylint: disable=broad-except
                _LOGGER.error("Unexpected exception: %s", exc)
                self._errors["base"] = "unknown"

            if "base" not in self._errors:
                await self.async_set_unique_id(
                    f"{user_input[CONF_NAME]}_{user_input[CONF_SERIAL]}"
                )

                return self.async_create_entry(
                    title=user_input[CONF_NAME],
                    data=user_input,
                    description=f"Vector robot: '{user_input[CONF_NAME]}'",
                )

        return self.async_show_form(
            step_id="user", data_schema=DATA_SCHEME, errors=self._errors
        )

    async def async_step_dhcp(
        self, discovery_info: DhcpServiceInfo
    ) -> ConfigFlowResult:
        """Handle DHCP discovery for Vector robots."""

        _LOGGER.debug("Discovered device: %s", discovery_info)
