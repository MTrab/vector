"""Vector robot update coordinator."""
# pylint: disable=unused-argument
# pylint: disable=no-member
from __future__ import annotations
import json

import logging
from datetime import datetime, timedelta
from enum import IntEnum
from typing import Optional
import grpc
import ha_vector

import pytz
from ha_vector.exceptions import VectorNotFoundException, VectorUnauthenticatedException
from ha_vector import messaging
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_NAME, EVENT_HOMEASSISTANT_STOP, STATE_UNKNOWN
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady, HomeAssistantError
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator


from .const import (
    CONF_ESCAPEPOD,
    CONF_IP,
    CONF_SERIAL,
    DOMAIN,
    STATE_ALIVE_DISTANCE,
    STATE_ALIVE_PET_MS,
    STATE_ALIVE_SECONDS,
    STATE_ALIVE_SENSOR_SCORE,
    STATE_ALIVE_TRIGGERWORDS,
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
from .helpers import Connection, DataSets, States
from .mappings import BATTERYMAP_TO_STATE, CUBE_BATTERYMAP_TO_STATE


_LOGGER = logging.getLogger(__name__)

SCAN_INTERVAL = timedelta(minutes=1)


class VectorConnectionState(IntEnum):
    """Class representing Vector Connection State."""

    UNKNOWN = 0
    CONNECTING = 1
    CONNECTED = 2
    DISCONNECTING = 3
    DISCONNECTED = 4


class VectorDataSetUpdateCoordinator(DataUpdateCoordinator[Optional[datetime]]):
    """Defines an update coordinator for keeping Vector datasets up-to-date."""

    def __init__(self, hass: HomeAssistant) -> None:
        """Initialize the connection."""
        DataUpdateCoordinator.__init__(
            self,
            hass=hass,
            logger=_LOGGER,
            name="vector_datasets",
            update_interval=timedelta(hours=24),
        )
        self._datasets = DataSets(hass)

    async def _async_update_data(self) -> None:
        """Update Vector datasets."""
        await self._datasets.async_refresh()


async def get_lifetime(conn) -> messaging.protocol.PullJdocsResponse:
    """Get lifetime stats from the robot."""
    req = messaging.protocol.PullJdocsRequest(
        jdoc_types=[
            messaging.settings_pb2.ROBOT_SETTINGS,
            messaging.settings_pb2.ROBOT_LIFETIME_STATS,
            messaging.settings_pb2.ACCOUNT_SETTINGS,
        ]
    )
    return await conn.grpc_interface.PullJdocs(req)


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
        )
        self.hass = hass
        self.entry = entry
        self.friendly_name = self.entry.data[CONF_NAME]
        self.serial = self.entry.data[CONF_SERIAL]
        self.vector_name = self.entry.data[CONF_NAME]
        self.full_name = f"{self.entry.data[CONF_NAME]}_{self.entry.data[CONF_SERIAL]}"
        self.config = hass.data[DOMAIN][self.entry.entry_id]["config"]
        self.datasets = hass.data[DOMAIN]["datasets"]
        self.states = States(self)

        try:
            self.robot = Connection(
                self.serial,
                behavior_control_level=None,
                cache_animation_lists=False,
                enable_face_detection=True,
                enable_nav_map_feed=True,
                name=self.vector_name,
                escape_pod=self.entry.data[CONF_ESCAPEPOD],
                ip=self.entry.data[CONF_IP],
                config=self.config,
            )
        except Exception:  # pylint: disable=bare-except
            raise ConfigEntryNotReady("Error setting up VectorHandler object") from None

        try:
            self.robot.connect()
        except VectorNotFoundException:
            raise HomeAssistantError("Unable to connect to the robot!") from None
        except VectorUnauthenticatedException as exc:
            _LOGGER.debug(exc.status)
            if exc.status == grpc.StatusCode.RESOURCE_EXHAUSTED:
                raise ConfigEntryNotReady(
                    "Too many auth requests, try again later"
                ) from exc

        hass.bus.async_listen_once(
            EVENT_HOMEASSISTANT_STOP, self.async_disconnect(hass=hass, coordinator=self)
        )

    async def async_disconnect(
        self, hass: HomeAssistant, coordinator: VectorDataUpdateCoordinator
    ) -> None:
        """Disconnect and cleanup after us."""
        # await self.async_unsubscribe_events()

        try:
            await hass.async_add_executor_job(coordinator.robot.disconnect)
        except:  # pylint: disable=bare-except
            pass

    async def async_subscribe_events(self) -> None:
        """Subscribe events."""
        await self.hass.data[DOMAIN][self.entry.entry_id]["events"].async_subscribe()

    async def async_unsubscribe_events(self) -> None:
        """Unsubscribe events."""
        await self.hass.data[DOMAIN][self.entry.entry_id]["events"].async_unsubscribe()

    async def _async_update_data(self) -> datetime | None:
        """Handle data update request from the coordinator."""
        battery_state = self.robot.get_battery_state().result(timeout=10)
        version_state = self.robot.get_version_state().result(timeout=10)
        lifetime_state = self.robot.conn.run_coroutine(
            get_lifetime(self.robot.conn)
        ).result(timeout=10)

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

        if lifetime_state:
            for jdoc in lifetime_state.named_jdocs:
                if (
                    jdoc.jdoc_type
                    == ha_vector.messaging.settings_pb2.ROBOT_LIFETIME_STATS
                ):
                    data = json.loads(jdoc.doc.json_doc)
                    _LOGGER.debug(jdoc)
                    self.states.set_robot_attribute(
                        STATE_ALIVE_SECONDS, data["Alive.seconds"]
                    )
                    self.states.set_robot_attribute(
                        STATE_ALIVE_TRIGGERWORDS, data["BStat.ReactedToTriggerWord"]
                    )
                    self.states.set_robot_attribute(
                        STATE_ALIVE_PET_MS, int(data["Pet.ms"] / 100)
                    )
                    self.states.set_robot_attribute(
                        STATE_ALIVE_DISTANCE, int(data["Odom.Body"] / 1000000)
                    )
                    self.states.set_robot_attribute(
                        STATE_ALIVE_SENSOR_SCORE, int(data["Stim.CumlPosDelta"] / 10)
                    )

        return True
