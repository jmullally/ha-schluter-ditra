"""Data update coordinator for Schluter DITRA-HEAT."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta
import logging
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.util import dt as dt_util

from .api import SchluterApi, SchluterAuthError, SchluterError
from .const import (
    DOMAIN,
    ENERGY_INTERVAL,
    FAMILY_FLOOR_THERMOSTAT,
    SCAN_INTERVAL,
    THERMOSTAT_ATTRIBUTES,
)

_LOGGER = logging.getLogger(__name__)

SchluterConfigEntry = ConfigEntry["SchluterCoordinator"]


@dataclass
class DeviceData:
    """State for one thermostat."""

    info: dict[str, Any]
    attrs: dict[str, Any] = field(default_factory=dict)
    # Energy in Wh
    energy_today: float | None = None
    energy_yesterday: float | None = None
    energy_month: float | None = None
    energy_last_hour: float | None = None


@dataclass
class SchluterData:
    locations: dict[int, dict[str, Any]] = field(default_factory=dict)
    devices: dict[int, DeviceData] = field(default_factory=dict)


class SchluterCoordinator(DataUpdateCoordinator[SchluterData]):
    """Polls locations, device attributes and energy history."""

    config_entry: SchluterConfigEntry

    def __init__(
        self, hass: HomeAssistant, entry: SchluterConfigEntry, api: SchluterApi
    ) -> None:
        super().__init__(
            hass,
            _LOGGER,
            config_entry=entry,
            name=DOMAIN,
            update_interval=SCAN_INTERVAL,
        )
        self.api = api
        self._last_slow_refresh: datetime | None = None

    async def _async_update_data(self) -> SchluterData:
        try:
            return await self._fetch()
        except SchluterAuthError as err:
            raise ConfigEntryAuthFailed(str(err)) from err
        except SchluterError as err:
            raise UpdateFailed(str(err)) from err

    async def _fetch(self) -> SchluterData:
        now = dt_util.utcnow()
        slow_due = (
            self.data is None
            or self._last_slow_refresh is None
            or now - self._last_slow_refresh >= ENERGY_INTERVAL
        )
        data = self.data or SchluterData()

        if slow_due:
            # Device list and energy history change slowly.
            locations: dict[int, dict[str, Any]] = {}
            devices: dict[int, DeviceData] = {}
            for loc in await self.api.get_locations():
                locations[loc["id"]] = loc
                for dev in await self.api.get_devices(loc["id"]):
                    if str(dev.get("family")) != FAMILY_FLOOR_THERMOSTAT:
                        continue
                    old = data.devices.get(dev["id"])
                    devices[dev["id"]] = DeviceData(
                        info=dev, attrs=old.attrs if old else {}
                    )
            data = SchluterData(locations=locations, devices=devices)
            for dev_id, dev in devices.items():
                await self._fetch_energy(dev_id, dev)
            self._last_slow_refresh = now
        else:
            # Location mode (home/away) is cheap and user-visible; keep it fresh.
            for loc_id in data.locations:
                data.locations[loc_id] = await self.api.get_location(loc_id)

        for dev_id, dev in data.devices.items():
            dev.attrs.update(
                await self.api.get_attributes(dev_id, THERMOSTAT_ATTRIBUTES)
            )
        return data

    async def _fetch_energy(self, dev_id: int, dev: DeviceData) -> None:
        try:
            hourly = await self.api.get_consumption(dev_id, "hourly")
            daily = await self.api.get_consumption(dev_id, "daily")
            monthly = await self.api.get_consumption(dev_id, "monthly")
        except SchluterError as err:
            _LOGGER.debug("Energy history unavailable for %s: %s", dev_id, err)
            return

        today = dt_util.now().date()
        yesterday = today - timedelta(days=1)
        dev.energy_today = _period_for(daily, today.isoformat(), default=0)
        dev.energy_yesterday = _period_for(daily, yesterday.isoformat(), default=None)
        dev.energy_month = _period_for(monthly, today.strftime("%Y-%m"), default=0)
        # The API reports completed hours only; the newest entry is the last full hour.
        dev.energy_last_hour = hourly[-1]["period"] if hourly else None


def _period_for(history: list[dict], key: str, default: float | None) -> float | None:
    """Return the Wh 'period' value for the entry matching a date prefix.

    Daily/monthly entries are stamped at midnight UTC of the local calendar day,
    so matching on the date string prefix is correct.
    """
    for entry in reversed(history):
        if str(entry.get("date", "")).startswith(key):
            return entry.get("period")
    return default
