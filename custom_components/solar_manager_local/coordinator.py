from __future__ import annotations

import logging
from numbers import Real
from typing import Any

from aiohttp import ClientError

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import (
    CONF_API_KEY,
    CONF_API_KEY_SECRET,
    CONF_BASE_URL,
    DEFAULT_API_KEY_SECRET,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
    ENDPOINT_POINT,
    REQUEST_TIMEOUT_SECONDS,
)
from .secrets import async_get_secret_value

LOGGER = logging.getLogger(__name__)


class SolarManagerDataCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        self._entry = entry
        self._session = async_get_clientsession(hass)
        self._base_url: str = str(entry.data[CONF_BASE_URL]).rstrip("/")
        self._api_key: str | None = entry.data.get(CONF_API_KEY)
        self._api_key_secret: str = entry.data.get(
            CONF_API_KEY_SECRET, DEFAULT_API_KEY_SECRET
        )
        self._produced_energy_kwh: float = 0.0
        self._last_interval_timestamp: str | None = None

        super().__init__(
            hass,
            logger=LOGGER,
            name=DOMAIN,
            update_interval=DEFAULT_SCAN_INTERVAL,
        )

    def set_initial_produced_energy_kwh(self, value: float) -> None:
        if value >= 0:
            self._produced_energy_kwh = value

    @property
    def produced_energy_kwh(self) -> float:
        return self._produced_energy_kwh

    async def _async_update_data(self) -> dict[str, Any]:
        url = f"{self._base_url}{ENDPOINT_POINT}"
        headers = {"Accept": "application/json"}
        api_key = self._api_key
        if not api_key:
            api_key = await async_get_secret_value(self.hass, self._api_key_secret)
        if api_key:
            headers["X-API-Key"] = api_key

        try:
            async with self._session.get(
                url,
                headers=headers,
                timeout=REQUEST_TIMEOUT_SECONDS,
                ssl=False,
            ) as response:
                if response.status != 200:
                    text = await response.text()
                    raise UpdateFailed(
                        f"Solar Manager API error ({response.status}): {text[:200]}"
                    )

                data = await response.json()
        except (ClientError, TimeoutError, ValueError) as err:
            raise UpdateFailed(f"Error communicating with Solar Manager API: {err}") from err

        if not isinstance(data, dict):
            raise UpdateFailed("Invalid response from Solar Manager API: expected JSON object")

        timestamp = data.get("t")
        interval_production_wh = data.get("pWh")

        if isinstance(interval_production_wh, Real):
            should_accumulate = True
            if isinstance(timestamp, str):
                if timestamp == self._last_interval_timestamp:
                    should_accumulate = False
                else:
                    self._last_interval_timestamp = timestamp

            if should_accumulate and interval_production_wh >= 0:
                self._produced_energy_kwh += float(interval_production_wh) / 1000

        data["energy_produced_total_kwh"] = self._produced_energy_kwh

        return data