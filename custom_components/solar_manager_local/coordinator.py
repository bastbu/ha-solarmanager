from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api_client import SolarManagerApiClient, SolarManagerApiError
from .const import (
    CONF_API_KEY,
    CONF_API_KEY_SECRET,
    CONF_BASE_URL,
    DEFAULT_API_KEY_SECRET,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
)
from .models import PointData
from .secrets import async_get_secret_value

LOGGER = logging.getLogger(__name__)


class SolarManagerDataCoordinator(DataUpdateCoordinator[PointData]):
    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        self._entry = entry
        self._api_key: str | None = entry.data.get(CONF_API_KEY)
        self._api_key_secret: str = entry.data.get(
            CONF_API_KEY_SECRET, DEFAULT_API_KEY_SECRET
        )
        self._base_url: str = str(entry.data[CONF_BASE_URL]).rstrip("/")
        self._client: SolarManagerApiClient | None = None
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

    async def _ensure_client(self) -> SolarManagerApiClient:
        """Lazily create the API client (resolves secret on first call)."""
        if self._client is None:
            api_key = self._api_key
            if not api_key:
                api_key = await async_get_secret_value(self.hass, self._api_key_secret)
            session = async_get_clientsession(self.hass)
            self._client = SolarManagerApiClient(session, self._base_url, api_key or "")
        return self._client

    async def _async_update_data(self) -> PointData:
        client = await self._ensure_client()

        try:
            point = await client.async_get_point()
        except SolarManagerApiError as err:
            raise UpdateFailed(str(err)) from err

        should_accumulate = True
        if point.timestamp and point.timestamp == self._last_interval_timestamp:
            should_accumulate = False
        elif point.timestamp:
            self._last_interval_timestamp = point.timestamp

        if should_accumulate and point.interval_production_wh >= 0:
            self._produced_energy_kwh += point.interval_production_wh / 1000

        return point