"""Number entities for Schluter DITRA-HEAT settings."""

from __future__ import annotations

from dataclasses import dataclass

from homeassistant.components.number import (
    NumberDeviceClass,
    NumberEntity,
    NumberEntityDescription,
    NumberMode,
)
from homeassistant.const import EntityCategory, UnitOfPower, UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .coordinator import SchluterConfigEntry
from .entity import SchluterDeviceEntity


@dataclass(frozen=True, kw_only=True)
class SchluterNumberDescription(NumberEntityDescription):
    attribute: str


TEMP_LIMITS = dict(
    device_class=NumberDeviceClass.TEMPERATURE,
    native_unit_of_measurement=UnitOfTemperature.CELSIUS,
    native_min_value=5,
    native_max_value=36,
    native_step=0.5,
    mode=NumberMode.BOX,
    entity_category=EntityCategory.CONFIG,
)

NUMBERS: tuple[SchluterNumberDescription, ...] = (
    SchluterNumberDescription(
        key="away_setpoint",
        name="Away setpoint",
        icon="mdi:home-export-outline",
        attribute="roomSetpointAway",
        **TEMP_LIMITS,
    ),
    SchluterNumberDescription(
        key="setpoint_min",
        name="Minimum setpoint",
        attribute="roomSetpointMin",
        **TEMP_LIMITS,
    ),
    SchluterNumberDescription(
        key="setpoint_max",
        name="Maximum setpoint",
        attribute="roomSetpointMax",
        **TEMP_LIMITS,
    ),
    SchluterNumberDescription(
        key="floor_sensor_offset",
        name="Floor probe offset",
        icon="mdi:thermometer-plus",
        attribute="floorSensorOffset",
        device_class=NumberDeviceClass.TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        native_min_value=-2,
        native_max_value=2,
        native_step=0.5,
        mode=NumberMode.BOX,
        entity_category=EntityCategory.CONFIG,
        entity_registry_enabled_default=False,
    ),
    SchluterNumberDescription(
        key="connected_load",
        name="Connected load",
        icon="mdi:flash",
        attribute="loadWattOutput1",
        device_class=NumberDeviceClass.POWER,
        native_unit_of_measurement=UnitOfPower.WATT,
        native_min_value=0,
        native_max_value=3600,
        native_step=1,
        mode=NumberMode.BOX,
        entity_category=EntityCategory.CONFIG,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: SchluterConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    coordinator = entry.runtime_data
    async_add_entities(
        SchluterNumber(coordinator, dev_id, desc)
        for dev_id, dev in coordinator.data.devices.items()
        for desc in NUMBERS
        if desc.attribute in dev.attrs
    )


class SchluterNumber(SchluterDeviceEntity, NumberEntity):
    entity_description: SchluterNumberDescription

    def __init__(self, coordinator, device_id: int, description: SchluterNumberDescription) -> None:
        super().__init__(coordinator, device_id, description.key)
        self.entity_description = description

    @property
    def native_value(self) -> float | None:
        return self.attrs.get(self.entity_description.attribute)

    async def async_set_native_value(self, value: float) -> None:
        if self.entity_description.native_step == 1:
            value = int(value)
        await self.async_set_attributes({self.entity_description.attribute: value})
