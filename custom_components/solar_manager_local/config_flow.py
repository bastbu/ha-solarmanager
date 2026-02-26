from __future__ import annotations

from typing import Any

import voluptuous as vol
from aiohttp import ClientError, ClientTimeout

from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import (
    CONF_API_KEY_SECRET,
    CONF_BASE_URL,
    DEFAULT_API_KEY_SECRET,
    DOMAIN,
    ENDPOINT_POINT,
    NAME,
    REQUEST_TIMEOUT_SECONDS,
)
from .secrets import async_get_secret_value


class SolarManagerConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(self, user_input: dict[str, Any] | None = None):
        errors: dict[str, str] = {}

        if user_input is not None:
            base_url = str(user_input[CONF_BASE_URL]).rstrip("/")
            api_key_secret = str(user_input.get(CONF_API_KEY_SECRET, "")).strip()

            await self.async_set_unique_id(base_url)
            self._abort_if_unique_id_configured()

            try:
                await _async_validate_input(self.hass, base_url, api_key_secret)
            except CannotConnect:
                errors["base"] = "cannot_connect"
            except SecretNotFound:
                errors["base"] = "secret_not_found"
            except InvalidResponse:
                errors["base"] = "invalid_response"
            except Exception:
                errors["base"] = "unknown"
            else:
                data = {
                    CONF_BASE_URL: base_url,
                    CONF_API_KEY_SECRET: api_key_secret,
                }
                return self.async_create_entry(title=NAME, data=data)

        schema = vol.Schema(
            {
                vol.Required(CONF_BASE_URL): str,
                vol.Required(CONF_API_KEY_SECRET, default=DEFAULT_API_KEY_SECRET): str,
            }
        )

        return self.async_show_form(step_id="user", data_schema=schema, errors=errors)


async def _async_validate_input(
    hass: HomeAssistant, base_url: str, api_key_secret: str
) -> None:
    session = async_get_clientsession(hass)
    api_key = await async_get_secret_value(hass, api_key_secret)
    if not api_key:
        raise SecretNotFound

    headers = {"Accept": "application/json"}
    headers["X-API-Key"] = api_key

    try:
        async with session.get(
            f"{base_url}{ENDPOINT_POINT}",
            headers=headers,
            timeout=ClientTimeout(total=REQUEST_TIMEOUT_SECONDS),
            ssl=False,
        ) as response:
            if response.status != 200:
                raise CannotConnect

            payload = await response.json()
    except (ClientError, TimeoutError, ValueError) as err:
        raise CannotConnect from err

    if not isinstance(payload, dict):
        raise InvalidResponse


class CannotConnect(Exception):
    pass


class InvalidResponse(Exception):
    pass


class SecretNotFound(Exception):
    pass