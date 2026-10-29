"""Binary sensors for Schluter DITRA-HEAT thermostats."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
    BinarySensorEntityDescription,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .coordinator import DeviceData, SchluterConfigEntry
from .entity import SchluterDeviceEntity


@dataclass(frozen=True, kw_only=True)
class SchluterBinaryDescription(BinarySensorEntityDescription):
    value_fn: Callable[[DeviceData], bool | None]
    requires: str


def _heating(d: DeviceData) -> bool | None:
    percent = (d.attrs.get("outputPercentDisplay") or {}).get("percent")
    return None if percent is None else percent > 0


BINARY_SENSORS: tuple[SchluterBinaryDescription, ...] = (
    SchluterBinaryDescription(
        key="heating",
        name="Heating",
        device_class=BinarySensorDeviceClass.HEAT,
        value_fn=_heating,
        requires="outputPercentDisplay",
    ),
    SchluterBinaryDescription(
        key="gfci_fault",
        name="GFCI fault",
        device_class=BinarySensorDeviceClass.PROBLEM,
        value_fn=lambda d: (
            None if d.attrs.get("gfciStatus") is None else d.attrs["gfciStatus"] != "ok"
        ),
        requires="gfciStatus",
    ),
    SchluterBinaryDescription(
        key="device_error",
        name="Device error",
        device_class=BinarySensorDeviceClass.PROBLEM,
        value_fn=lambda d: bool((d.attrs.get("errorCodeSet1") or {}).get("raw")),
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
        SchluterBinarySensor(coordinator, dev_id, desc)
        for dev_id, dev in coordinator.data.devices.items()
        for desc in BINARY_SENSORS
        if desc.requires in dev.attrs
    )


class SchluterBinarySensor(SchluterDeviceEntity, BinarySensorEntity):
    entity_description: SchluterBinaryDescription

    def __init__(self, coordinator, device_id: int, description: SchluterBinaryDescription) -> None:
        super().__init__(coordinator, device_id, description.key)
        self.entity_description = description

    @property
    def is_on(self) -> bool | None:
        return self.entity_description.value_fn(self.device)
