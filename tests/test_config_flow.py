from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from homeassistant.data_entry_flow import AbortFlow

from custom_components.solar_manager_local.config_flow import (
    CannotConnect,
    InvalidResponse,
    SecretNotFound,
    SolarManagerConfigFlow,
    _async_validate_input,
)
from custom_components.solar_manager_local.const import (
    CONF_API_KEY,
    CONF_API_KEY_SECRET,
    CONF_BASE_URL,
)


@pytest.fixture
def flow() -> SolarManagerConfigFlow:
    flow = SolarManagerConfigFlow()
    flow.hass = MagicMock()
    return flow


@pytest.fixture
def entry() -> MagicMock:
    entry = MagicMock()
    entry.entry_id = "test-entry"
    entry.data = {
        CONF_BASE_URL: "http://192.168.1.20",
        CONF_API_KEY_SECRET: "solar_manager_api_key",
    }
    return entry


async def test_reconfigure_prefills_existing_values(
    flow: SolarManagerConfigFlow, entry: MagicMock
) -> None:
    with patch.object(flow, "_get_reconfigure_entry", return_value=entry):
        result = await flow.async_step_reconfigure()

    assert result["step_id"] == "reconfigure"
    assert result["data_schema"]({}) == {CONF_BASE_URL: entry.data[CONF_BASE_URL]}


@pytest.mark.parametrize("base_url", ["http://192.168.1.20", "http://192.168.1.30"])
async def test_reconfigure_updates_and_reloads(
    flow: SolarManagerConfigFlow, entry: MagicMock, base_url: str
) -> None:
    entry.data[CONF_API_KEY] = "legacy-key"
    entry.data["other_setting"] = "preserved"
    with (
        patch.object(flow, "_get_reconfigure_entry", return_value=entry),
        patch.object(flow, "_async_current_entries", return_value=[entry]),
        patch(
            "custom_components.solar_manager_local.config_flow._async_validate_input",
            new_callable=AsyncMock,
        ) as validate,
        patch.object(flow, "async_update_reload_and_abort") as update,
    ):
        flow.context = {"entry_id": entry.entry_id}
        await flow.async_step_reconfigure(
            {CONF_BASE_URL: f" {base_url}/ ", CONF_API_KEY: " new_key "}
        )

    validate.assert_awaited_once_with(flow.hass, base_url, "new_key")
    update.assert_called_once_with(
        entry,
        unique_id=base_url,
        data={
            CONF_BASE_URL: base_url,
            CONF_API_KEY: "new_key",
            "other_setting": "preserved",
        },
    )
    assert entry.data[CONF_BASE_URL] == "http://192.168.1.20"


@pytest.mark.parametrize(
    ("exception", "error"),
    [
        (CannotConnect, "cannot_connect"),
        (SecretNotFound, "secret_not_found"),
        (InvalidResponse, "invalid_response"),
        (RuntimeError, "unknown"),
    ],
)
async def test_reconfigure_validation_failure_keeps_entry(
    flow: SolarManagerConfigFlow, entry: MagicMock, exception: type[Exception], error: str
) -> None:
    values = {CONF_BASE_URL: "http://192.168.1.30", CONF_API_KEY: "new_key"}
    with (
        patch.object(flow, "_get_reconfigure_entry", return_value=entry),
        patch.object(flow, "_async_current_entries", return_value=[]),
        patch(
            "custom_components.solar_manager_local.config_flow._async_validate_input",
            side_effect=exception,
        ),
        patch.object(flow, "async_update_reload_and_abort") as update,
    ):
        result = await flow.async_step_reconfigure(values)

    assert result["errors"] == {"base": error}
    assert result["data_schema"]({}) == {CONF_BASE_URL: values[CONF_BASE_URL]}
    update.assert_not_called()
    assert entry.data[CONF_BASE_URL] == "http://192.168.1.20"


async def test_reconfigure_rejects_another_entries_address(
    flow: SolarManagerConfigFlow, entry: MagicMock
) -> None:
    other_entry = MagicMock()
    other_entry.entry_id = "other-entry"
    other_entry.data = {CONF_BASE_URL: "http://192.168.1.30"}
    with (
        patch.object(flow, "_get_reconfigure_entry", return_value=entry),
        patch.object(flow, "_async_current_entries", return_value=[entry, other_entry]),
        patch(
            "custom_components.solar_manager_local.config_flow._async_validate_input",
            new_callable=AsyncMock,
        ) as validate,
    ):
        flow.context = {"entry_id": entry.entry_id}
        with pytest.raises(AbortFlow) as raised:
            await flow.async_step_reconfigure(
                {CONF_BASE_URL: "http://192.168.1.30", CONF_API_KEY: "new_key"}
            )

    assert raised.value.reason == "already_configured"
    validate.assert_not_awaited()


async def test_setup_uses_masked_key_field(flow: SolarManagerConfigFlow) -> None:
    result = await flow.async_step_user()
    schema = result["data_schema"].schema
    assert schema[CONF_API_KEY].config["type"] == "password"
    assert CONF_API_KEY_SECRET not in schema


async def test_setup_stores_validated_key(flow: SolarManagerConfigFlow) -> None:
    with (
        patch.object(flow, "async_set_unique_id", new_callable=AsyncMock),
        patch.object(flow, "_abort_if_unique_id_configured"),
        patch(
            "custom_components.solar_manager_local.config_flow._async_validate_input",
            new_callable=AsyncMock,
        ) as validate,
        patch.object(flow, "async_create_entry") as create,
    ):
        await flow.async_step_user(
            {CONF_BASE_URL: " http://192.168.1.20/ ", CONF_API_KEY: " new-key "}
        )

    validate.assert_awaited_once_with(flow.hass, "http://192.168.1.20", "new-key")
    assert create.call_args.kwargs["data"] == {
        CONF_BASE_URL: "http://192.168.1.20",
        CONF_API_KEY: "new-key",
    }


@pytest.mark.parametrize("submitted_key", [None, "", "   "])
@pytest.mark.parametrize("legacy", [False, True])
async def test_reconfigure_keeps_credentials_when_key_is_blank(
    flow: SolarManagerConfigFlow, entry: MagicMock, submitted_key: str | None, legacy: bool
) -> None:
    if not legacy:
        entry.data = {CONF_BASE_URL: "http://192.168.1.20", CONF_API_KEY: "saved-key"}
    values = {CONF_BASE_URL: "http://192.168.1.30"}
    if submitted_key is not None:
        values[CONF_API_KEY] = submitted_key

    with (
        patch.object(flow, "_get_reconfigure_entry", return_value=entry),
        patch.object(flow, "_async_current_entries", return_value=[]),
        patch(
            "custom_components.solar_manager_local.config_flow.async_get_secret_value",
            new_callable=AsyncMock,
            return_value="saved-key",
        ) as secret,
        patch(
            "custom_components.solar_manager_local.config_flow._async_validate_input",
            new_callable=AsyncMock,
        ) as validate,
        patch.object(flow, "async_update_reload_and_abort") as update,
    ):
        form = await flow.async_step_reconfigure()
        assert form["data_schema"]({}) == {CONF_BASE_URL: entry.data[CONF_BASE_URL]}
        assert form["data_schema"].schema[CONF_API_KEY].config["type"] == "password"
        await flow.async_step_reconfigure(values)

    validate.assert_awaited_once_with(flow.hass, "http://192.168.1.30", "saved-key")
    assert update.call_args.kwargs["data"] == {
        **entry.data,
        CONF_BASE_URL: "http://192.168.1.30",
    }
    if legacy:
        secret.assert_awaited_once_with(flow.hass, "solar_manager_api_key")
    else:
        secret.assert_not_awaited()


async def test_reconfigure_reports_missing_legacy_secret(
    flow: SolarManagerConfigFlow, entry: MagicMock
) -> None:
    with (
        patch.object(flow, "_get_reconfigure_entry", return_value=entry),
        patch.object(flow, "_async_current_entries", return_value=[]),
        patch(
            "custom_components.solar_manager_local.config_flow.async_get_secret_value",
            new_callable=AsyncMock,
            return_value=None,
        ),
        patch.object(flow, "async_update_reload_and_abort") as update,
    ):
        result = await flow.async_step_reconfigure({CONF_BASE_URL: "http://192.168.1.30"})

    assert result["errors"] == {"base": "secret_not_found"}
    update.assert_not_called()


async def test_validation_uses_key_without_reading_secrets(
    flow: SolarManagerConfigFlow,
) -> None:
    with (
        patch("custom_components.solar_manager_local.config_flow.async_get_clientsession"),
        patch("custom_components.solar_manager_local.config_flow.SolarManagerApiClient") as client,
        patch(
            "custom_components.solar_manager_local.config_flow.async_get_secret_value",
            new_callable=AsyncMock,
        ) as secret,
    ):
        client.return_value.async_get_point = AsyncMock()
        await _async_validate_input(flow.hass, "http://192.168.1.20", "entered-key")

    assert client.call_args.args[1:] == ("http://192.168.1.20", "entered-key")
    client.return_value.async_get_point.assert_awaited_once()
    secret.assert_not_awaited()