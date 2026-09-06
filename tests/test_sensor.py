from __future__ import annotations

from collections.abc import Iterable
from typing import cast
from unittest.mock import MagicMock, patch

from homeassistant.helpers.entity import Entity

from custom_components.solar_manager_local.const import DOMAIN
from custom_components.solar_manager_local.models import DeviceData, PointData
from custom_components.solar_manager_local.sensor import (
    SolarManagerDeviceSensor,
    async_setup_entry,
)


async def test_child_devices_use_gateway_registry_id() -> None:
    device = DeviceData(
        device_id="device-123456",
        power=100,
        signal="good",
        temperature=None,
        active_device=None,
        import_energy_wh=0,
        export_energy_wh=0,
    )
    coordinator = MagicMock()
    coordinator.data = PointData(100, 50, 10, "timestamp", [device])

    entry = MagicMock()
    entry.entry_id = "test-entry"
    hass = MagicMock()
    hass.data = {DOMAIN: {entry.entry_id: coordinator}}

    gateway_device = MagicMock()
    gateway_device.id = "gateway-registry-id"
    registry = MagicMock()
    registry.async_get_or_create.return_value = gateway_device
    added_entities: list[Entity] = []

    def add_entities(
        new_entities: Iterable[Entity], update_before_add: bool = False
    ) -> None:
        added_entities.extend(new_entities)

    with patch(
        "custom_components.solar_manager_local.sensor.dr.async_get",
        return_value=registry,
    ):
        await async_setup_entry(hass, entry, add_entities)

    child_entities = [
        entity
        for entity in added_entities
        if isinstance(entity, SolarManagerDeviceSensor)
    ]
    assert child_entities
    assert all(
        cast(dict[str, object], entity.device_info).get("via_device_id")
        == gateway_device.id
        and "via_device" not in cast(dict[str, object], entity.device_info)
        for entity in child_entities
    )