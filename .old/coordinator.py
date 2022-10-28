"""Base definition of DDL Vector."""
# pylint: disable=unused-argument
from __future__ import annotations

import logging
from datetime import datetime, timedelta
from enum import IntEnum
from typing import Optional

import pytz
from ha_vector.exceptions import VectorTimeoutException
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_NAME, EVENT_HOMEASSISTANT_STOP, STATE_UNKNOWN
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers.event import async_call_later
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from .const import (
    BATTERYMAP_TO_STATE,
    CONF_IP,
    CONF_SERIAL,
    CUBE_BATTERYMAP_TO_STATE,
    DOMAIN,
    STATE_CHARGNING,
    STATE_CUBE_BATTERY_VOLTS,
    STATE_CUBE_FACTORY_ID,
    STATE_CUBE_LAST_CONTACT,
    STATE_FIRMWARE_VERSION,
    STATE_ROBOT_BATTERY_VOLTS,
    STATE_ROBOT_IS_CHARGNING,
    STATE_ROBOT_IS_ON_CHARGER,
    STATE_ROBOT_SUGGESTED_CHARGE,
)
from .vector_utils import VectorHandler
from .vector_utils.states_handler import VectorState

_LOGGER = logging.getLogger(__name__)

SCAN_INTERVAL = timedelta(minutes=1)


class VectorConnectionState(IntEnum):
    """Class representing Vector Connection State."""

    UNKNOWN = 0
    CONNECTING = 1
    CONNECTED = 2
    DISCONNECTING = 3
    DISCONNECTED = 4


class VectorDataUpdateCoordinator(DataUpdateCoordinator[Optional[datetime]]):
    """Defines a Vector data update coordinator."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        """Initialize the connection."""
        DataUpdateCoordinator.__init__(
            self,
            hass=hass,
            logger=_LOGGER,
            name=entry.data[CONF_NAME],
            update_interval=SCAN_INTERVAL,
            update_method=self.async_update,
        )
        self.hass = hass
        self._entry = entry
        self.friendly_name = self._entry.data[CONF_NAME]
        self.serial = self._entry.data[CONF_SERIAL]
        self.vector_name = self._entry.data[CONF_NAME]
        self.full_name = (
            f"{self._entry.data[CONF_NAME]}_{self._entry.data[CONF_SERIAL]}"
        )
        self._config = hass.data[DOMAIN][self._entry.entry_id]["config"]
        self.store = hass.data[DOMAIN][self._entry.entry_id]["datastore"]
        self.states = VectorState(hass, self.name)

        try:
            self.robot = VectorHandler(
                self.serial,
                behavior_control_level=None,
                cache_animation_lists=False,
                enable_face_detection=True,
                name=self._entry.data[CONF_NAME],
                ip_address=self._entry.data[CONF_IP],
                config=self._config,
                force_async=True,
            )
        except Exception:  # pylint: disable=bare-except
            raise ConfigEntryNotReady("Error setting up VectorHandler object") from None

        self.robot.connect()

        def load_anim_list() -> None:
            try:
                self.robot.anim.load_animation_list()
            except VectorTimeoutException:
                _LOGGER.debug(
                    "Couldn't load animations list, got a timeout - trying again in 5 seconds."
                )
                async_call_later(hass, timedelta(seconds=5), load_anim_list)

        try:
            self.robot.vision.enable_face_detection(
                detect_faces=True, estimate_expression=True
            )
            load_anim_list()
        except Exception:  # pylint: disable=broad-except
            pass

        hass.bus.async_listen_once(
            EVENT_HOMEASSISTANT_STOP, self.async_disconnect(hass=hass, coordinator=self)
        )

    async def async_subscribe_events(self) -> None:
        """Subscribe events."""
        await self.hass.data[DOMAIN][self._entry.entry_id]["events"].async_subscribe()

    async def async_unsubscribe_events(self) -> None:
        """Unsubscribe events."""
        await self.hass.data[DOMAIN][self._entry.entry_id]["events"].async_unsubscribe()

    async def async_update(self) -> datetime | None:
        """Update Vector data."""
        # try:
        battery_state = self.robot.get_battery_state().result(timeout=10)
        version_state = self.robot.get_version_state().result(timeout=10)

        if battery_state:
            self.states.robot_battery_state(
                BATTERYMAP_TO_STATE[battery_state.battery_level]
                if not battery_state.is_charging
                else STATE_CHARGNING
            )
            self.states.robot_battery_attributes(
                STATE_ROBOT_BATTERY_VOLTS, round(battery_state.battery_volts, 2)
            )
            self.states.robot_battery_attributes(
                STATE_ROBOT_IS_CHARGNING, battery_state.is_charging
            )
            self.states.robot_battery_attributes(
                STATE_ROBOT_IS_ON_CHARGER, battery_state.is_on_charger_platform
            )
            self.states.robot_battery_attributes(
                STATE_ROBOT_SUGGESTED_CHARGE, battery_state.suggested_charger_sec
            )

            if hasattr(battery_state, "cube_battery"):
                cube_battery = battery_state.cube_battery
                self.states.cube_battery_state(
                    CUBE_BATTERYMAP_TO_STATE[cube_battery.level]
                    if not cube_battery.battery_volts == 0.0
                    else STATE_UNKNOWN
                )
                self.states.cube_battery_attributes(
                    {
                        STATE_CUBE_BATTERY_VOLTS: round(cube_battery.battery_volts, 2),
                        STATE_CUBE_FACTORY_ID: cube_battery.factory_id,
                        STATE_CUBE_LAST_CONTACT: (
                            datetime.utcnow()
                            - timedelta(
                                seconds=int(cube_battery.time_since_last_reading_sec)
                            )
                        ).astimezone(pytz.UTC),
                    }
                )
            else:
                self.states.cube_battery_state(STATE_UNKNOWN)

        if version_state:
            self.states.set_robot_attribute(
                STATE_FIRMWARE_VERSION, version_state.os_version
            )

        return True
        # except concurrent.futures.TimeoutError:
        #     self.update_interval = None

        #     raise HomeAssistantError(
        #         f"Timeout communicating with {self.vector_name}"
        #     ) from None

        # except VectorConnectionException:
        #     self.update_interval = None

        #     try:
        #         await self.async_disconnect(self.hass, self)
        #     except:  # pylint: disable=bare-except
        #         pass

        #     raise ConfigEntryNotReady(
        #         f"Error communicating with {self.vector_name}"
        #     ) from None
        # except Exception:
        #     self.update_interval = None

        #     try:
        #         await self.async_disconnect(self.hass, self)
        #     except:  # pylint: disable=bare-except
        #         pass

        #     raise ConfigEntryNotReady(
        #         f"Generic Error communicating with {self.vector_name}"
        #     ) from None

    async def async_disconnect(
        self, hass: HomeAssistant, coordinator: VectorDataUpdateCoordinator
    ) -> None:
        """Disconnect and cleanup after us."""
        await self.async_unsubscribe_events()

        try:
            await hass.async_add_executor_job(coordinator.robot.disconnect)
        except:  # pylint: disable=bare-except
            pass
