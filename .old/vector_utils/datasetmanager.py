"""Handler for refreshing JSON datasets."""
from __future__ import annotations

import logging
import os
from datetime import datetime
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.json import json

from .const import BASE_URL, DATASETS
from .exceptions import VectorDatasetException

_LOGGER = logging.getLogger(__name__)


class DataRunner:
    """Data runner class."""

    def __init__(self, hass: HomeAssistant, save_path: str) -> None:
        """Initialize data runner object."""
        self.last_refresh: datetime = None
        self._client = async_get_clientsession(hass)
        self._save_path = save_path

    async def async_refresh(self) -> None:
        """Refresh all datasets."""
        for data in DATASETS.items():
            if data[1]:
                _LOGGER.debug("Refreshing dataset %s", data[1])
                await self.__async_fetch_dataset(data[1])

    async def __async_fetch_dataset(self, filename: str) -> None:
        """Fetch dataset."""
        data_url = (BASE_URL).format(filename)
        res = await self._client.get(data_url)

        if res.status != 200:
            raise VectorDatasetException(f"Error fetching dataset from {data_url}")

        dataset = await res.json(content_type="text/plain")
        await self.__async_save_dataset(filename, dataset)

    async def __async_save_dataset(self, filename: str, dataset: Any) -> None:
        """Save dataset to local destination."""
        os.makedirs(str(self._save_path), exist_ok=True)
        fullname = str(f"{self._save_path}/{filename}")
        with os.fdopen(
            os.open(fullname, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o666), "w"
        ) as file:
            json.dump(dataset, file)

    @property
    def path(self) -> str:
        """Returns the path to the datasets."""
        return self._save_path
