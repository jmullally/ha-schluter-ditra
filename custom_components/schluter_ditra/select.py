"""Select entities for Schluter DITRA-HEAT settings and location mode."""

from __future__ import annotations

from dataclasses import dataclass

from homeassistant.components.select import SelectEntity, SelectEntityDescription
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .api import SchluterError
from .coordinator import SchluterConfigEntry
from .entity import SchluterDeviceEntity, SchluterLocationEntity


@dataclass(frozen=True, kw_only=True)
class SchluterSelectDescription(SelectEntityDescription):
    attribute: str
    # Friendly label -> API value
    choices: dict[str, str]


SELECTS: tuple[SchluterSelectDescription, ...] = (
    SchluterSelectDescription(
        key="keypad_lock",
        name="Keypad lock",
        icon="mdi:lock",
        entity_category=EntityCategory.CONFIG,
        attribute="keyboardLock",
        choices={"Unlocked": "unlock", "Locked": "lock", "Partially locked": "partialLock"},
    ),
    SchluterSelectDescription(
        key="backlight",
        name="Backlight",
        icon="mdi:brightness-6",
        entity_category=EntityCategory.CONFIG,
        attribute="backlightAutoDim",
        choices={"Always on": "alwaysOn", "Bedroom (dims)": "bedroom"},
    ),
    SchluterSelectDescription(
        key="control_mode",
        name="Control mode",
        icon="mdi:floor-plan",
        entity_category=EntityCategory.CONFIG,
        attribute="airFloorMode",
        choices={"Floor": "floor", "Ambient": "roomByFloor"},
    ),
    SchluterSelectDescription(
        key="secondary_display",
        name="Secondary display",
        icon="mdi:monitor",
        entity_category=EntityCategory.CONFIG,
        attribute="config2ndDisplay",
        choices={"Setpoint": "setpoint", "Outside temperature": "exteriorTemperature"},
    ),
    SchluterSelectDescription(
        key="temperature_format",
        name="Display temperature unit",
        icon="mdi:thermometer",
        entity_category=EntityCategory.CONFIG,
        attribute="temperatureFormat",
        choices={"Celsius": "celsius", "Fahrenheit": "fahrenheit"},
    ),
    SchluterSelectDescription(
        key="time_format",
        name="Display time format",
        icon="mdi:clock-outline",
        entity_category=EntityCategory.CONFIG,
        attribute="timeFormat",
        choices={"12 h": "12h", "24 h": "24h"},
    ),
    SchluterSelectDescription(
        key="language",
        name="Display language",
        icon="mdi:translate",
        entity_category=EntityCategory.CONFIG,
        attribute="language",
        choices={"English": "en", "Français": "fr"},
        entity_registry_enabled_default=False,
    ),
    SchluterSelectDescription(
        key="floor_sensor_type",
        name="Floor probe type",
        icon="mdi:thermometer-probe",
        entity_category=EntityCategory.CONFIG,
        attribute="floorSensorType",
        choices={"10k": "10k", "12k": "12k"},
        entity_registry_enabled_default=False,
    ),
)

LOCATION_MODES = {"Home": "home", "Away": "away"}


async def async_setup_entry(
    hass: HomeAssistant,
    entry: SchluterConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    coordinator = entry.runtime_data
    entities: list[SelectEntity] = [
        SchluterSelect(coordinator, dev_id, desc)
        for dev_id, dev in coordinator.data.devices.items()
        for desc in SELECTS
        if desc.attribute in dev.attrs
    ]
    entities.extend(
        SchluterLocationModeSelect(coordinator, loc_id)
        for loc_id in coordinator.data.locations
    )
    async_add_entities(entities)


class SchluterSelect(SchluterDeviceEntity, SelectEntity):
    entity_description: SchluterSelectDescription

    def __init__(self, coordinator, device_id: int, description: SchluterSelectDescription) -> None:
        super().__init__(coordinator, device_id, description.key)
        self.entity_description = description
        self._attr_options = list(description.choices)

    @property
    def current_option(self) -> str | None:
        value = self.attrs.get(self.entity_description.attribute)
        for label, api_value in self.entity_description.choices.items():
            if api_value == value:
                return label
        return None

    async def async_select_option(self, option: str) -> None:
        await self.async_set_attributes(
            {self.entity_description.attribute: self.entity_description.choices[option]}
        )


class SchluterLocationModeSelect(SchluterLocationEntity, SelectEntity):
    """Home/Away for the whole location (applies each device's away setpoint)."""

    _attr_name = "Presence"
    _attr_icon = "mdi:home-account"
    _attr_options = list(LOCATION_MODES)

    def __init__(self, coordinator, location_id: int) -> None:
        super().__init__(coordinator, location_id, "mode")

    @property
    def current_option(self) -> str | None:
        mode = self.location.get("mode")
        return next((k for k, v in LOCATION_MODES.items() if v == mode), None)

    async def async_select_option(self, option: str) -> None:
        try:
            result = await self.coordinator.api.set_location_mode(
                self._location_id, LOCATION_MODES[option]
            )
        except SchluterError as err:
            raise HomeAssistantError(f"Failed to set presence: {err}") from err
        self.location["mode"] = (result or {}).get("mode", LOCATION_MODES[option])
        # Device setpoints change with the location mode; pull them now.
        await self.coordinator.async_request_refresh()
