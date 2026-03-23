"""Integration tests for the Solar Manager local API.

These tests exercise the production ``SolarManagerApiClient`` against a
real Solar Manager device.  Configure connection details in a ``.env``
file at the project root (see ``.env.example``).
"""

from __future__ import annotations

import os
from pathlib import Path

import aiohttp
import pytest
from dotenv import load_dotenv

from custom_components.solar_manager_local.api_client import (
    SolarManagerApiClient,
    SolarManagerApiError,
)
from custom_components.solar_manager_local.models import PointData

# Load .env from the project root
load_dotenv(Path(__file__).resolve().parents[1] / ".env")

BASE_URL: str = os.environ.get("SOLAR_MANAGER_BASE_URL", "")
API_KEY: str = os.environ.get("SOLAR_MANAGER_API_KEY", "")

pytestmark = pytest.mark.skipif(
    not BASE_URL or not API_KEY,
    reason="SOLAR_MANAGER_BASE_URL and SOLAR_MANAGER_API_KEY must be set in .env",
)


@pytest.fixture
async def session():
    async with aiohttp.ClientSession() as s:
        yield s


@pytest.fixture
async def client(session: aiohttp.ClientSession) -> SolarManagerApiClient:
    return SolarManagerApiClient(session, BASE_URL, API_KEY)


# ------------------------------------------------------------------
# Connectivity
# ------------------------------------------------------------------


async def test_get_point_returns_point_data(client: SolarManagerApiClient) -> None:
    """async_get_point returns a PointData instance."""
    data = await client.async_get_point()
    assert isinstance(data, PointData)


async def test_invalid_api_key_raises(session: aiohttp.ClientSession) -> None:
    """An invalid API key causes SolarManagerApiError."""
    bad_client = SolarManagerApiClient(session, BASE_URL, "definitely-not-valid")
    with pytest.raises(SolarManagerApiError):
        await bad_client.async_get_point()


async def test_unreachable_host_raises(session: aiohttp.ClientSession) -> None:
    """A non-routable host causes SolarManagerApiError."""
    bad_client = SolarManagerApiClient(session, "http://192.0.2.1", API_KEY)
    with pytest.raises(SolarManagerApiError):
        await bad_client.async_get_point()


# ------------------------------------------------------------------
# Response structure / data types
# ------------------------------------------------------------------


async def test_response_contains_expected_fields(client: SolarManagerApiClient) -> None:
    """The response must populate the fields the integration relies on."""
    data = await client.async_get_point()
    assert isinstance(data.production_power_w, float)
    assert isinstance(data.consumption_power_w, float)
    assert isinstance(data.interval_production_wh, float)
    assert isinstance(data.timestamp, str)
    assert data.timestamp != ""


async def test_power_values_are_numeric(client: SolarManagerApiClient) -> None:
    """production_power_w and consumption_power_w are floats."""
    data = await client.async_get_point()
    assert isinstance(data.production_power_w, float)
    assert isinstance(data.consumption_power_w, float)


async def test_interval_energy_is_numeric(client: SolarManagerApiClient) -> None:
    """interval_production_wh is a float."""
    data = await client.async_get_point()
    assert isinstance(data.interval_production_wh, float)


async def test_timestamp_is_string(client: SolarManagerApiClient) -> None:
    """timestamp is a non-empty string."""
    data = await client.async_get_point()
    assert isinstance(data.timestamp, str)
    assert len(data.timestamp) > 0


async def test_production_power_non_negative(client: SolarManagerApiClient) -> None:
    """PV production power should not be negative."""
    data = await client.async_get_point()
    assert data.production_power_w >= 0


async def test_raw_dict_preserved(client: SolarManagerApiClient) -> None:
    """The raw dict from the API is preserved on PointData."""
    data = await client.async_get_point()
    assert isinstance(data.raw, dict)
    assert "pW" in data.raw


# ------------------------------------------------------------------
# Consecutive reads
# ------------------------------------------------------------------


async def test_consecutive_reads_return_valid_data(
    client: SolarManagerApiClient,
) -> None:
    """Two rapid consecutive calls both succeed."""
    for _ in range(2):
        data = await client.async_get_point()
        assert isinstance(data, PointData)
        assert isinstance(data.production_power_w, float)
