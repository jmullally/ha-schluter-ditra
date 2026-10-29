"""Diagnostics for Schluter DITRA-HEAT."""

from __future__ import annotations

from dataclasses import asdict
from typing import Any

from homeassistant.components.diagnostics import async_redact_data
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME
from homeassistant.core import HomeAssistant

from .coordinator import SchluterConfigEntry

REDACT = {
    CONF_USERNAME,
    CONF_PASSWORD,
    "identifier",
    "address",
    "postalCode",
    "latitude",
    "longitude",
}


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: SchluterConfigEntry
) -> dict[str, Any]:
    data = entry.runtime_data.data
    return async_redact_data(
        {
            "entry": dict(entry.data),
            "locations": data.locations,
            "devices": {str(k): asdict(v) for k, v in data.devices.items()},
        },
        REDACT,
    )
