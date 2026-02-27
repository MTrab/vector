"""The Vector integration."""

from __future__ import annotations

import asyncio
from typing import TypedDict

import voluptuous as vol
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import ATTR_DEVICE_ID
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady, ServiceValidationError
from homeassistant.helpers import config_validation as cv, device_registry as dr

from .const import PLATFORMS
from .coordinator import VectorCoordinator
from .const import (
    ATTR_DURATION_SCALAR,
    ATTR_PITCH_SCALAR,
    ATTR_TEXT,
    ATTR_USE_VECTOR_VOICE,
    DOMAIN,
    SERVICE_SAY_TEXT,
)

_SETUP_VALIDATION_TIMEOUT_SECONDS = 20.0


class VectorRuntimeData(TypedDict):
    """Runtime data stored on config entries."""

    coordinator: VectorCoordinator
    start_task: asyncio.Task[None] | None


class VectorDomainData(TypedDict):
    """Runtime data stored on hass.data for this integration domain."""

    coordinators: dict[str, VectorCoordinator]


_SAY_TEXT_SERVICE_SCHEMA = vol.Schema(
    {
        vol.Required(ATTR_TEXT): cv.string,
        vol.Optional(ATTR_DEVICE_ID): vol.Any(None, cv.string, [cv.string]),
        vol.Optional(ATTR_USE_VECTOR_VOICE, default=True): cv.boolean,
        vol.Optional(ATTR_DURATION_SCALAR, default=1.0): vol.Coerce(float),
        vol.Optional(ATTR_PITCH_SCALAR, default=0.0): vol.Coerce(float),
    }
)


def _get_or_create_domain_data(hass: HomeAssistant) -> VectorDomainData:
    """Return mutable domain-scoped runtime data."""
    if DOMAIN not in hass.data:
        hass.data[DOMAIN] = {"coordinators": {}}
    return hass.data[DOMAIN]


def _resolve_target_coordinator(
    *,
    hass: HomeAssistant,
    coordinators: dict[str, VectorCoordinator],
    device_id: str | None,
) -> VectorCoordinator:
    if device_id is not None:
        device_registry = dr.async_get(hass)
        device = device_registry.async_get(device_id)
        if device is None:
            raise ServiceValidationError(f"Unknown device_id: {device_id}")

        matching_entry_ids = [
            config_entry_id
            for config_entry_id in device.config_entries
            if config_entry_id in coordinators
        ]
        if not matching_entry_ids:
            raise ServiceValidationError(
                f"Device {device_id} is not associated with a configured Vector entry."
            )
        if len(matching_entry_ids) > 1:
            raise ServiceValidationError(
                f"Device {device_id} maps to multiple Vector entries."
            )

        coordinator = coordinators[matching_entry_ids[0]]
        return coordinator

    if len(coordinators) == 1:
        return next(iter(coordinators.values()))

    raise ServiceValidationError(
        "Multiple Vector entries configured. Provide device_id."
    )


def _extract_device_id(call_data: dict[str, str | bool | float | list[str] | None]) -> str | None:
    raw = call_data.get(ATTR_DEVICE_ID)
    if raw is None:
        return None
    if isinstance(raw, str):
        return raw
    if isinstance(raw, list):
        if not raw:
            return None
        if len(raw) > 1:
            raise ServiceValidationError(
                "Select exactly one Vector device for this action."
            )
        return raw[0]
    raise ServiceValidationError("device_id must be a string or list of one string")


async def _async_handle_say_text_service(
    hass: HomeAssistant,
    call_data: dict[str, str | bool | float | list[str] | None],
) -> None:
    domain_data = _get_or_create_domain_data(hass)
    coordinator = _resolve_target_coordinator(
        hass=hass,
        coordinators=domain_data["coordinators"],
        device_id=_extract_device_id(call_data),
    )

    text = call_data[ATTR_TEXT]
    if not isinstance(text, str):
        raise ServiceValidationError("text must be a string")

    try:
        await coordinator.async_say_text(
            text=text,
            use_vector_voice=bool(call_data.get(ATTR_USE_VECTOR_VOICE, True)),
            duration_scalar=float(call_data.get(ATTR_DURATION_SCALAR, 1.0)),
            pitch_scalar=float(call_data.get(ATTR_PITCH_SCALAR, 0.0)),
        )
    except ValueError as err:
        raise ServiceValidationError(str(err)) from err


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Vector from a config entry."""
    coordinator = VectorCoordinator(hass, entry)

    try:
        await asyncio.wait_for(
            coordinator.async_validate_connection(),
            timeout=_SETUP_VALIDATION_TIMEOUT_SECONDS,
        )
    except TimeoutError as err:
        await coordinator.async_shutdown()
        raise ConfigEntryNotReady(
            f"Timed out validating Vector connection after {_SETUP_VALIDATION_TIMEOUT_SECONDS:.0f}s"
        ) from err
    except Exception as err:
        await coordinator.async_shutdown()
        raise ConfigEntryNotReady(
            f"Failed to validate Vector connection: {err}"
        ) from err

    entry.runtime_data = {
        "coordinator": coordinator,
        "start_task": None,
    }
    domain_data = _get_or_create_domain_data(hass)
    domain_data["coordinators"][entry.entry_id] = coordinator

    if not hass.services.has_service(DOMAIN, SERVICE_SAY_TEXT):
        hass.services.async_register(
            DOMAIN,
            SERVICE_SAY_TEXT,
            lambda call: _async_handle_say_text_service(hass, call.data),
            schema=_SAY_TEXT_SERVICE_SCHEMA,
        )

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    start_task = hass.async_create_background_task(
        coordinator.async_start_runtime(),
        name=f"vector_start_{entry.entry_id}",
    )
    entry.runtime_data["start_task"] = start_task
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        runtime_data: VectorRuntimeData | None = entry.runtime_data
        if runtime_data:
            start_task = runtime_data.get("start_task")
            if start_task is not None:
                start_task.cancel()
            coordinator = runtime_data.get("coordinator")
            if coordinator is not None:
                await coordinator.async_shutdown()
            entry.runtime_data = None

        domain_data = hass.data.get(DOMAIN)
        if domain_data is not None:
            coordinators = domain_data.get("coordinators", {})
            coordinators.pop(entry.entry_id, None)
            if not coordinators:
                hass.services.async_remove(DOMAIN, SERVICE_SAY_TEXT)
                hass.data.pop(DOMAIN, None)
    return unload_ok
