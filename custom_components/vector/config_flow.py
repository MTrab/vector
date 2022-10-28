"""Digital Dream Labs Vector integration config flow."""
from __future__ import annotations

import logging

import voluptuous as vol
from homeassistant import config_entries, exceptions
from homeassistant.const import CONF_EMAIL, CONF_NAME, CONF_PASSWORD

from .vector_utils.config import validate_input
from .const import CONF_IP, CONF_SERIAL, DOMAIN

_LOGGER = logging.getLogger(__name__)

DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_EMAIL): str,
        vol.Required(CONF_PASSWORD): str,
        vol.Required(CONF_NAME): str,
        vol.Required(CONF_SERIAL): str,
        vol.Required(CONF_IP): str,
    }
)


class DDLVectorConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for DDL Vector."""

    VERSION = 1
    CONNECTION_CLASS = config_entries.CONN_CLASS_CLOUD_POLL

    def check_for_existing(self, data):
        """Check whether an existing entry is using the same URLs."""
        return any(
            entry.data.get(CONF_NAME) == data.get(CONF_NAME)
            and entry.data.get(CONF_SERIAL) == data.get(CONF_SERIAL)
            and entry.data.get(CONF_EMAIL) == data.get(CONF_EMAIL)
            and entry.data.get(CONF_PASSWORD) == data.get(CONF_PASSWORD)
            for entry in self._async_current_entries()
        )

    def __init__(self):
        """Initialize the config flow."""
        self._errors = {}

    async def async_step_user(self, user_input=None):
        """Handle the initial DDL Vector step."""
        self._errors = {}
        if user_input is not None:
            if self.check_for_existing(user_input):
                return self.async_abort(reason="already_exists")

            try:
                validated = await validate_input(self.hass, user_input)
            except CannotConnect:
                self._errors["base"] = "cannot_connect"
            except InvalidAuth:
                self._errors["base"] = "invalid_auth"
            except Exception:  # pylint: disable=broad-except
                _LOGGER.exception("Unexpected exception")
                self._errors["base"] = "unknown"

            if "base" not in self._errors:
                return self.async_create_entry(
                    title=user_input[CONF_NAME],
                    data=user_input,
                    description=f"SDK connector for {user_input[CONF_NAME]}",
                )

        return self.async_show_form(
            step_id="user", data_schema=DATA_SCHEMA, errors=self._errors
        )


class InvalidAuth(exceptions.HomeAssistantError):
    """Error to indicate there is invalid auth."""


class CannotConnect(exceptions.HomeAssistantError):
    """Error to indicate we cannot connect."""
