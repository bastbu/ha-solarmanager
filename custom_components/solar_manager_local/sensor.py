from __future__ import annotations

from dataclasses import dataclass
from numbers import Real
from typing import Any, Callable

from homeassistant.components.sensor import (
    RestoreSensor,
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfEnergy, UnitOfPower
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, NAME
from .coordinator import SolarManagerDataCoordinator


@dataclass(frozen=True, kw_only=True)
class SolarManagerSensorEntityDescription(SensorEntityDescription):
    value_fn: Callable[[dict[str, Any]], Real | None]


SENSOR_DESCRIPTIONS: tuple[SolarManagerSensorEntityDescription, ...] = (
    SolarManagerSensorEntityDescription(
        key="pv_production_power",
        name="PV production power",
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfPower.WATT,
        value_fn=lambda data: data.get("pW"),
    ),
    SolarManagerSensorEntityDescription(
        key="home_consumption_power",
        name="Home consumption power",
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfPower.WATT,
        value_fn=lambda data: data.get("cW"),
    ),
    SolarManagerSensorEntityDescription(
        key="pv_energy_produced_total",
        name="PV energy produced total",
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        value_fn=lambda data: data.get("energy_produced_total_kwh"),
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: SolarManagerDataCoordinator = hass.data[DOMAIN][entry.entry_id]
    entities: list[SolarManagerSensor] = []
    for description in SENSOR_DESCRIPTIONS:
        if description.key == "pv_energy_produced_total":
            entities.append(SolarManagerAccumulatedEnergySensor(coordinator, entry, description))
        else:
            entities.append(SolarManagerSensor(coordinator, entry, description))

    async_add_entities(entities)


class SolarManagerSensor(CoordinatorEntity[SolarManagerDataCoordinator], SensorEntity):  # pyright: ignore[reportIncompatibleVariableOverride]
    def __init__(
        self,
        coordinator: SolarManagerDataCoordinator,
        entry: ConfigEntry,
        description: SolarManagerSensorEntityDescription,
    ) -> None:
        super().__init__(coordinator)
        self.entity_description = description
        self._attr_unique_id = f"{entry.entry_id}_{description.key}"
        self._attr_device_info = {
            "identifiers": {(DOMAIN, entry.entry_id)},
            "name": NAME,
            "manufacturer": "Solar Manager",
        }
        self._attr_has_entity_name = True
        self._value_fn = description.value_fn

    def _handle_coordinator_update(self) -> None:
        value = self._value_fn(self.coordinator.data)
        if isinstance(value, Real):
            self._attr_native_value = float(value)
        else:
            self._attr_native_value = None
        super()._handle_coordinator_update()


class SolarManagerAccumulatedEnergySensor(SolarManagerSensor, RestoreSensor):  # pyright: ignore[reportIncompatibleVariableOverride]
    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()

        last_state = await self.async_get_last_state()
        if last_state is None:
            return

        try:
            restored_value = float(last_state.state)
        except (TypeError, ValueError):
            return

        self.coordinator.set_initial_produced_energy_kwh(restored_value)