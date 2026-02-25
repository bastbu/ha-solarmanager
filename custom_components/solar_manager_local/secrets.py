from __future__ import annotations

from pathlib import Path

import yaml

from homeassistant.core import HomeAssistant


async def async_get_secret_value(hass: HomeAssistant, secret_name: str) -> str | None:
    if not secret_name:
        return None

    secrets_path = Path(hass.config.path("secrets.yaml"))

    def _load_secret() -> str | None:
        if not secrets_path.exists():
            return None

        with secrets_path.open("r", encoding="utf-8") as file_handle:
            data = yaml.safe_load(file_handle) or {}

        if not isinstance(data, dict):
            return None

        value = data.get(secret_name)
        if value is None:
            return None

        result = str(value).strip()
        return result or None

    return await hass.async_add_executor_job(_load_secret)