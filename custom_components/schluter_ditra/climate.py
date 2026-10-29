"""Climate entity for Schluter DITRA-HEAT thermostats."""

from __future__ import annotations

from typing import Any

from homeassistant.components.climate import (
    PRESET_NONE,
    ClimateEntity,
    ClimateEntityFeature,
    HVACAction,
    HVACMode,
)
from homeassistant.const import ATTR_TEMPERATURE, UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .const import MODE_AUTO, MODE_AUTO_BYPASS, MODE_FROST, MODE_MANUAL, MODE_OFF
from .coordinator import SchluterConfigEntry
from .entity import SchluterDeviceEntity
from .helpers import temp_value

PRESET_FROST = "frost_protection"
PRESET_OVERRIDE = "temporary_override"

HVAC_TO_MODE = {
    HVACMode.HEAT: MODE_MANUAL,
    HVACMode.AUTO: MODE_AUTO,
    HVACMode.OFF: MODE_OFF,
}


async def async_setup_entry(
    hass: HomeAssistant,
    entry: SchluterConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    coordinator = entry.runtime_data
    async_add_entities(
        SchluterClimate(coordinator, dev_id) for dev_id in coordinator.data.devices
    )


class SchluterClimate(SchluterDeviceEntity, ClimateEntity):
    """Floor heating thermostat.

    HEAT = manual setpoint, AUTO = follow the cloud schedule, OFF = standby.
    """

    _attr_name = None
    _attr_temperature_unit = UnitOfTemperature.CELSIUS
    _attr_target_temperature_step = 0.5
    _attr_hvac_modes = [HVACMode.OFF, HVACMode.HEAT, HVACMode.AUTO]
    _attr_preset_modes = [PRESET_NONE, PRESET_FROST, PRESET_OVERRIDE]
    _attr_supported_features = (
        ClimateEntityFeature.TARGET_TEMPERATURE
        | ClimateEntityFeature.PRESET_MODE
        | ClimateEntityFeature.TURN_ON
        | ClimateEntityFeature.TURN_OFF
    )
    _attr_translation_key = "thermostat"

    def __init__(self, coordinator, device_id: int) -> None:
        super().__init__(coordinator, device_id, "climate")

    @property
    def _mode(self) -> str | None:
        return self.attrs.get("setpointMode")

    @property
    def current_temperature(self) -> float | None:
        # In floor mode the setpoint regulates the floor probe, so report that.
        if self.attrs.get("airFloorMode") == "floor":
            return temp_value(self.attrs.get("floorTemperature"))
        return temp_value(self.attrs.get("roomTemperature"))

    @property
    def target_temperature(self) -> float | None:
        if self._mode == MODE_OFF:
            return None
        return self.attrs.get("roomSetpoint")

    @property
    def min_temp(self) -> float:
        return self.attrs.get("roomSetpointMin") or 5

    @property
    def max_temp(self) -> float:
        return self.attrs.get("roomSetpointMax") or 36

    @property
    def hvac_mode(self) -> HVACMode | None:
        mode = self._mode
        if mode == MODE_OFF:
            return HVACMode.OFF
        if mode in (MODE_AUTO, MODE_AUTO_BYPASS):
            return HVACMode.AUTO
        if mode in (MODE_MANUAL, MODE_FROST):
            return HVACMode.HEAT
        return None

    @property
    def preset_mode(self) -> str | None:
        if self._mode == MODE_FROST:
            return PRESET_FROST
        if self._mode == MODE_AUTO_BYPASS:
            return PRESET_OVERRIDE
        return PRESET_NONE

    @property
    def hvac_action(self) -> HVACAction | None:
        if self._mode == MODE_OFF:
            return HVACAction.OFF
        output = self.attrs.get("outputPercentDisplay") or {}
        percent = output.get("percent")
        if percent is None:
            return None
        return HVACAction.HEATING if percent > 0 else HVACAction.IDLE

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        output = self.attrs.get("outputPercentDisplay") or {}
        return {
            "setpoint_mode": self._mode,
            "control_mode": self.attrs.get("airFloorMode"),
            "heating_output": output.get("percent"),
            "floor_temperature": temp_value(self.attrs.get("floorTemperature")),
            "room_temperature": temp_value(self.attrs.get("roomTemperature")),
        }

    async def async_set_temperature(self, **kwargs: Any) -> None:
        if (temp := kwargs.get(ATTR_TEMPERATURE)) is None:
            return
        await self.async_set_attributes({"roomSetpoint": round(temp * 2) / 2})

    async def async_set_hvac_mode(self, hvac_mode: HVACMode) -> None:
        await self.async_set_attributes({"setpointMode": HVAC_TO_MODE[hvac_mode]})

    async def async_set_preset_mode(self, preset_mode: str) -> None:
        if preset_mode == PRESET_FROST:
            mode = MODE_FROST
        elif preset_mode == PRESET_OVERRIDE:
            # An override only exists relative to the schedule; changing the
            # setpoint while in AUTO is what creates it.
            return
        elif self._mode in (MODE_AUTO, MODE_AUTO_BYPASS):
            mode = MODE_AUTO  # cancel a temporary override
        else:
            mode = MODE_MANUAL
        await self.async_set_attributes({"setpointMode": mode})

    async def async_turn_on(self) -> None:
        await self.async_set_hvac_mode(HVACMode.AUTO)

    async def async_turn_off(self) -> None:
        await self.async_set_hvac_mode(HVACMode.OFF)
