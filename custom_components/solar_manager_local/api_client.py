"""Thin async client for the Solar Manager local API."""

from __future__ import annotations

from aiohttp import ClientError, ClientSession, ClientTimeout

from .const import ENDPOINT_POINT, REQUEST_TIMEOUT_SECONDS
from .models import PointData


class SolarManagerApiClient:
    """Fetch data from a Solar Manager device over the local network."""

    def __init__(self, session: ClientSession, base_url: str, api_key: str) -> None:
        self._session = session
        self._base_url = base_url.rstrip("/")
        self._api_key = api_key

    async def async_get_point(self) -> PointData:
        """Call GET /v2/point and return the parsed response.

        Raises ``SolarManagerApiError`` on any communication / validation
        failure.
        """
        url = f"{self._base_url}{ENDPOINT_POINT}"
        headers: dict[str, str] = {"Accept": "application/json"}
        if self._api_key:
            headers["X-API-Key"] = self._api_key

        try:
            async with self._session.get(
                url,
                headers=headers,
                timeout=ClientTimeout(total=REQUEST_TIMEOUT_SECONDS),
                ssl=False,
            ) as response:
                if response.status != 200:
                    text = await response.text()
                    raise SolarManagerApiError(
                        f"API error ({response.status}): {text[:200]}"
                    )

                raw_data = await response.json()
        except (ClientError, TimeoutError, ValueError) as err:
            raise SolarManagerApiError(
                f"Error communicating with Solar Manager API: {err}"
            ) from err

        if not isinstance(raw_data, dict):
            raise SolarManagerApiError(
                "Invalid response from Solar Manager API: expected JSON object"
            )

        return PointData.from_dict(raw_data)


class SolarManagerApiError(Exception):
    """Raised when the Solar Manager API returns an unexpected result."""
