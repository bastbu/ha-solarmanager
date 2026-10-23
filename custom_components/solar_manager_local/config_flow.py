from __future__ import annotations

import logging
from typing import Any

from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.selector import TextSelector, TextSelectorConfig, TextSelectorType
import voluptuous as vol

from .api_client import SolarManagerApiClient, SolarManagerApiError
from .const import (
    CONF_API_KEY,
    CONF_API_KEY_SECRET,
    CONF_BASE_URL,
    DEFAULT_API_KEY_SECRET,
    DOMAIN,
    NAME,
)
from .secrets import async_get_secret_value

LOGGER = logging.getLogger(__name__)


class SolarManagerConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(self, user_input: dict[str, Any] | None = None):
        errors: dict[str, str] = {}

        if user_input is not None:
            base_url = str(user_input[CONF_BASE_URL]).strip().rstrip("/")
            api_key = str(user_input[CONF_API_KEY]).strip()

            await self.async_set_unique_id(base_url)
            self._abort_if_unique_id_configured()

            try:
                await _async_validate_input(self.hass, base_url, api_key)
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
                    CONF_API_KEY: api_key,
                }
                return self.async_create_entry(title=NAME, data=data)

        schema = vol.Schema(
            {
                vol.Required(CONF_BASE_URL): str,
                vol.Required(CONF_API_KEY): TextSelector(
                    TextSelectorConfig(type=TextSelectorType.PASSWORD)
                ),
            }
        )

        return self.async_show_form(step_id="user", data_schema=schema, errors=errors)

    async def async_step_reconfigure(
        self, user_input: dict[str, Any] | None = None
    ):
        entry = self._get_reconfigure_entry()
        errors: dict[str, str] = {}
        values = dict(entry.data)

        if user_input is not None:
            base_url = str(user_input[CONF_BASE_URL]).strip().rstrip("/")
            replacement_key = str(user_input.get(CONF_API_KEY, "")).strip()
            values[CONF_BASE_URL] = base_url
            self._async_abort_entries_match({CONF_BASE_URL: base_url})

            try:
                api_key = replacement_key or entry.data.get(CONF_API_KEY)
                if not api_key:
                    api_key = await async_get_secret_value(
                        self.hass,
                        entry.data.get(CONF_API_KEY_SECRET, DEFAULT_API_KEY_SECRET),
                    )
                    if not api_key:
                        raise SecretNotFound
                await _async_validate_input(self.hass, base_url, api_key)
            except CannotConnect:
                errors["base"] = "cannot_connect"
            except SecretNotFound:
                errors["base"] = "secret_not_found"
            except InvalidResponse:
                errors["base"] = "invalid_response"
            except Exception:
                LOGGER.error("Unexpected error reconfiguring Solar Manager")
                errors["base"] = "unknown"
            else:
                if replacement_key:
                    values[CONF_API_KEY] = replacement_key
                    values.pop(CONF_API_KEY_SECRET, None)
                return self.async_update_reload_and_abort(
                    entry, unique_id=base_url, data=values
                )

        schema = vol.Schema(
            {
                vol.Required(CONF_BASE_URL, default=values[CONF_BASE_URL]): str,
                vol.Optional(CONF_API_KEY): TextSelector(
                    TextSelectorConfig(type=TextSelectorType.PASSWORD)
                ),
            }
        )
        return self.async_show_form(
            step_id="reconfigure", data_schema=schema, errors=errors
        )


async def _async_validate_input(
    hass: HomeAssistant, base_url: str, api_key: str
) -> None:
    if not api_key:
        raise CannotConnect

    session = async_get_clientsession(hass)
    client = SolarManagerApiClient(session, base_url, api_key)

    try:
        await client.async_get_point()
    except SolarManagerApiError as err:
        raise CannotConnect from err


class CannotConnect(Exception):
    pass


class InvalidResponse(Exception):
    pass


class SecretNotFound(Exception):
    pass