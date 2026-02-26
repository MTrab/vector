"""Shared entity helpers for Vector integration."""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import CONF_HOST, CONF_ROBOT_NAME, CONF_SERIAL, DOMAIN
from .coordinator import VectorCoordinator


class VectorEntity(CoordinatorEntity[VectorCoordinator]):
    """Base entity with shared Vector device metadata."""

    def __init__(self, coordinator: VectorCoordinator, entry: ConfigEntry) -> None:
        """Initialize shared Vector entity state."""
        super().__init__(coordinator)
        self._entry = entry

    @property
    def _serial(self) -> str:
        runtime_serial = self.coordinator.robot_serial
        if isinstance(runtime_serial, str):
            normalized_runtime = runtime_serial.strip().lower()
            if normalized_runtime:
                return normalized_runtime

        entry_serial = self._entry.data.get(CONF_SERIAL)
        if isinstance(entry_serial, str):
            return entry_serial.strip().lower()

        return ""

    @property
    def _generation(self) -> str | None:
        """Return hardware generation based on serial format."""
        serial = self._serial
        if not serial:
            return None
        return "1.0" if serial.startswith("00") else "2.0"

    @property
    def _manufacturer(self) -> str:
        """Return vendor name based on generation."""
        generation = self._generation
        if generation == "1.0":
            return "Anki"
        if generation == "2.0":
            return "Digital Dream Labs"
        return "Anki / Digital Dream Labs"

    @property
    def device_info(self) -> DeviceInfo:
        """Return device metadata for this robot."""
        robot_name = self._entry.data[CONF_ROBOT_NAME]
        identifier = self._serial or self._entry.data.get(CONF_HOST) or robot_name
        return DeviceInfo(
            identifiers={(DOMAIN, identifier)},
            name=robot_name,
            manufacturer=self._manufacturer,
            model="Vector",
            hw_version=self._generation,
            sw_version=self.coordinator.firmware_version,
        )
