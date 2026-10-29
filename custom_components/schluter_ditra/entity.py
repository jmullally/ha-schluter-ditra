"""Base entities for Schluter DITRA-HEAT."""

from __future__ import annotations

from typing import Any

from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .api import SchluterError
from .const import DOMAIN, MANUFACTURER
from .coordinator import DeviceData, SchluterCoordinator


class SchluterDeviceEntity(CoordinatorEntity[SchluterCoordinator]):
    """An entity belonging to one thermostat."""

    _attr_has_entity_name = True

    def __init__(self, coordinator: SchluterCoordinator, device_id: int, key: str) -> None:
        super().__init__(coordinator)
        self._device_id = device_id
        self._attr_unique_id = f"{device_id}_{key}"
        info = self.device.info
        sig = info.get("signature") or {}
        sw = sig.get("softVersion") or {}
        location = coordinator.data.locations.get(info.get("location$id"), {})
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, str(device_id))},
            name=info.get("name"),
            manufacturer=info.get("vendor") or MANUFACTURER,
            model=info.get("sku") or f"Family {info.get('family')}",
            sw_version=".".join(str(sw[k]) for k in ("major", "middle", "minor") if k in sw)
            or None,
            hw_version=str(sig["hardRev"]) if "hardRev" in sig else None,
            suggested_area=location.get("name") if location else None,
            configuration_url=(
                f"https://schluterditraheat.com/locations/{info.get('location$id')}"
                f"/devices/{device_id}"
            ),
        )

    @property
    def device(self) -> DeviceData:
        return self.coordinator.data.devices[self._device_id]

    @property
    def attrs(self) -> dict[str, Any]:
        return self.device.attrs

    @property
    def available(self) -> bool:
        return super().available and self._device_id in self.coordinator.data.devices

    async def async_set_attributes(self, values: dict[str, Any]) -> None:
        """Write attributes to the device and apply the echoed values locally."""
        try:
            result = await self.coordinator.api.set_attributes(self._device_id, values)
        except SchluterError as err:
            raise HomeAssistantError(f"Failed to update {self.entity_id}: {err}") from err
        self.attrs.update(result if isinstance(result, dict) else values)
        self.coordinator.async_update_listeners()


class SchluterLocationEntity(CoordinatorEntity[SchluterCoordinator]):
    """An entity belonging to a location (home)."""

    _attr_has_entity_name = True

    def __init__(self, coordinator: SchluterCoordinator, location_id: int, key: str) -> None:
        super().__init__(coordinator)
        self._location_id = location_id
        self._attr_unique_id = f"location_{location_id}_{key}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, f"location_{location_id}")},
            name=f"Schluter {self.location.get('name') or 'Location'}",
            manufacturer=MANUFACTURER,
            model="Location",
            configuration_url=f"https://schluterditraheat.com/locations/{location_id}/dashboard",
        )

    @property
    def location(self) -> dict[str, Any]:
        return self.coordinator.data.locations.get(self._location_id, {})

    @property
    def available(self) -> bool:
        return super().available and self._location_id in self.coordinator.data.locations
