"""Configure the Vector instance params."""
from __future__ import annotations

from ha_vector.setup import VectorSetup
from homeassistant.const import CONF_EMAIL, CONF_NAME, CONF_PASSWORD
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from ..const import CONF_CERTIFICATE, CONF_GUID, CONF_IP, CONF_SERIAL
from ..helpers import VectorStore


async def validate_input(hass: HomeAssistant, data: dict) -> bool:
    """Validate the user input allows us to connect.
    Data has the keys from DATA_SCHEMA with values provided by the user.
    """
    store = VectorStore(hass, data[CONF_NAME])
    await store.async_load()
    vector_api = VectorSetup(
        data[CONF_EMAIL],
        data[CONF_PASSWORD],
        data[CONF_NAME],
        data[CONF_SERIAL],
        data[CONF_IP],
        store.cert_path,
        async_get_clientsession(hass),
    )

    await vector_api.async_configure()

    config = {
        CONF_CERTIFICATE: vector_api.certificate,
        CONF_NAME: data[CONF_NAME],
        CONF_GUID: vector_api.guid.replace("b'", "").replace("'", ""),
    }

    await store.async_save(config)

    return True
