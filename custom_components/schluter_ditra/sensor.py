"""Sensors for Schluter DITRA-HEAT thermostats."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.const import (
    PERCENTAGE,
    SIGNAL_STRENGTH_DECIBELS_MILLIWATT,
    EntityCategory,
    UnitOfEnergy,
    UnitOfPower,
    UnitOfTemperature,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .coordinator import DeviceData, SchluterConfigEntry
from .entity import SchluterDeviceEntity
from .helpers import limit_value, temp_value


def _output_percent(d: DeviceData) -> Any:
    return (d.attrs.get("outputPercentDisplay") or {}).get("percent")


def _power(d: DeviceData) -> Any:
    """Instantaneous draw: duty cycle x configured load."""
    load = d.attrs.get("loadWattOutput1")
    percent = _output_percent(d)
    if load is None or percent is None:
        return None
    return round(load * percent / 100)


def _wh_to_kwh(value: float | None) -> float | None:
    return None if value is None else round(value / 1000, 3)


@dataclass(frozen=True, kw_only=True)
class SchluterSensorDescription(SensorEntityDescription):
    value_fn: Callable[[DeviceData], Any]
    # Attribute that must be present for the entity to be created.
    requires: str | None = None


SENSORS: tuple[SchluterSensorDescription, ...] = (
    SchluterSensorDescription(
        key="floor_temperature",
        name="Floor temperature",
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        suggested_display_precision=1,
        value_fn=lambda d: temp_value(d.attrs.get("floorTemperature")),
        requires="floorTemperature",
    ),
    SchluterSensorDescription(
        key="room_temperature",
        name="Room temperature",
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        suggested_display_precision=1,
        value_fn=lambda d: temp_value(d.attrs.get("roomTemperature")),
        requires="roomTemperature",
    ),
    SchluterSensorDescription(
        key="heating_output",
        name="Heating output",
        icon="mdi:radiator",
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=PERCENTAGE,
        value_fn=_output_percent,
        requires="outputPercentDisplay",
    ),
    SchluterSensorDescription(
        key="power",
        name="Power",
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfPower.WATT,
        value_fn=_power,
        requires="loadWattOutput1",
    ),
    SchluterSensorDescription(
        key="energy_today",
        name="Energy today",
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        suggested_display_precision=2,
        value_fn=lambda d: _wh_to_kwh(d.energy_today),
    ),
    SchluterSensorDescription(
        key="energy_yesterday",
        name="Energy yesterday",
        device_class=SensorDeviceClass.ENERGY,
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        suggested_display_precision=2,
        value_fn=lambda d: _wh_to_kwh(d.energy_yesterday),
    ),
    SchluterSensorDescription(
        key="energy_month",
        name="Energy this month",
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        suggested_display_precision=2,
        value_fn=lambda d: _wh_to_kwh(d.energy_month),
    ),
    SchluterSensorDescription(
        key="energy_last_hour",
        name="Energy last hour",
        device_class=SensorDeviceClass.ENERGY,
        native_unit_of_measurement=UnitOfEnergy.WATT_HOUR,
        value_fn=lambda d: d.energy_last_hour,
        entity_registry_enabled_default=False,
    ),
    SchluterSensorDescription(
        key="wifi_signal",
        name="Wi-Fi signal",
        device_class=SensorDeviceClass.SIGNAL_STRENGTH,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=SIGNAL_STRENGTH_DECIBELS_MILLIWATT,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda d: d.attrs.get("wifiRssi"),
        requires="wifiRssi",
    ),
    SchluterSensorDescription(
        key="floor_limit_high",
        name="Floor high limit",
        device_class=SensorDeviceClass.TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda d: limit_value(d.attrs.get("floorLimitHigh")),
        requires="floorLimitHigh",
        entity_registry_enabled_default=False,
    ),
    SchluterSensorDescription(
        key="floor_limit_low",
        name="Floor low limit",
        device_class=SensorDeviceClass.TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda d: limit_value(d.attrs.get("floorLimitLow")),
        requires="floorLimitLow",
        entity_registry_enabled_default=False,
    ),
    SchluterSensorDescription(
        key="ambient_limit",
        name="Ambient limit",
        device_class=SensorDeviceClass.TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda d: limit_value(d.attrs.get("floorMaxAirTemperature")),
        requires="floorMaxAirTemperature",
        entity_registry_enabled_default=False,
    ),
    SchluterSensorDescription(
        key="error_code",
        name="Error code",
        icon="mdi:alert-circle-outline",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda d: (d.attrs.get("errorCodeSet1") or {}).get("raw"),
        requires="errorCodeSet1",
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: SchluterConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    coordinator = entry.runtime_data
    async_add_entities(
        SchluterSensor(coordinator, dev_id, desc)
        for dev_id, dev in coordinator.data.devices.items()
        for desc in SENSORS
        if desc.requires is None or desc.requires in dev.attrs
    )


class SchluterSensor(SchluterDeviceEntity, SensorEntity):
    entity_description: SchluterSensorDescription

    def __init__(self, coordinator, device_id: int, description: SchluterSensorDescription) -> None:
        super().__init__(coordinator, device_id, description.key)
        self.entity_description = description

    @property
    def native_value(self) -> Any:
        return self.entity_description.value_fn(self.device)
