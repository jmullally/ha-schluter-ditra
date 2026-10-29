"""Switch entities for Schluter DITRA-HEAT settings."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from homeassistant.components.switch import SwitchEntity, SwitchEntityDescription
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .coordinator import SchluterConfigEntry
from .entity import SchluterDeviceEntity


@dataclass(frozen=True, kw_only=True)
class SchluterSwitchDescription(SwitchEntityDescription):
    attribute: str
    on_value: Any
    off_value: Any


SWITCHES: tuple[SchluterSwitchDescription, ...] = (
    SchluterSwitchDescription(
        key="early_start",
        name="Early start",
        icon="mdi:clock-fast",
        entity_category=EntityCategory.CONFIG,
        attribute="earlyStartCfg",
        on_value="on",
        off_value="off",
    ),
    SchluterSwitchDescription(
        key="gfci_alert",
        name="GFCI alert",
        icon="mdi:flash-alert",
        entity_category=EntityCategory.CONFIG,
        attribute="alertGfci",
        on_value=True,
        off_value=False,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: SchluterConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    coordinator = entry.runtime_data
    async_add_entities(
        SchluterSwitch(coordinator, dev_id, desc)
        for dev_id, dev in coordinator.data.devices.items()
        for desc in SWITCHES
        if desc.attribute in dev.attrs
    )


class SchluterSwitch(SchluterDeviceEntity, SwitchEntity):
    entity_description: SchluterSwitchDescription

    def __init__(self, coordinator, device_id: int, description: SchluterSwitchDescription) -> None:
        super().__init__(coordinator, device_id, description.key)
        self.entity_description = description

    @property
    def is_on(self) -> bool | None:
        value = self.attrs.get(self.entity_description.attribute)
        if value is None:
            return None
        return value == self.entity_description.on_value

    async def async_turn_on(self, **kwargs: Any) -> None:
        await self.async_set_attributes(
            {self.entity_description.attribute: self.entity_description.on_value}
        )

    async def async_turn_off(self, **kwargs: Any) -> None:
        await self.async_set_attributes(
            {self.entity_description.attribute: self.entity_description.off_value}
        )
