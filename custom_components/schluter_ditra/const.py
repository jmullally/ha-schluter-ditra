"""Constants for the Schluter DITRA-HEAT integration."""

from datetime import timedelta

DOMAIN = "schluter_ditra"
MANUFACTURER = "Schluter"

BASE_URL = "https://schluterditraheat.com/api"
INTERFACE = "schluter"
APP_VERSION = "1.13.3"

SCAN_INTERVAL = timedelta(seconds=60)
ENERGY_INTERVAL = timedelta(minutes=15)

# Device family used by the DITRA-HEAT-E-RS1 floor thermostat.
FAMILY_FLOOR_THERMOSTAT = "740"

# Attributes polled for each floor thermostat. Attributes the device does not
# support are simply omitted from the response.
THERMOSTAT_ATTRIBUTES = [
    "roomTemperature",
    "floorTemperature",
    "roomTemperatureDisplay",
    "roomSetpoint",
    "roomSetpointMin",
    "roomSetpointMax",
    "roomSetpointAway",
    "setpointMode",
    "occupancyMode",
    "airFloorMode",
    "outputPercentDisplay",
    "loadWatt",
    "loadWattOutput1",
    "gfciStatus",
    "alertGfci",
    "errorCodeSet1",
    "keyboardLock",
    "backlightAutoDim",
    "config2ndDisplay",
    "earlyStartCfg",
    "temperatureFormat",
    "timeFormat",
    "language",
    "floorSensorType",
    "floorSensorOffset",
    "floorLimitHigh",
    "floorLimitLow",
    "floorMaxAirTemperature",
    "wifiRssi",
]

# setpointMode values
MODE_MANUAL = "manual"
MODE_AUTO = "auto"
MODE_AUTO_BYPASS = "autoBypass"
MODE_OFF = "off"
MODE_FROST = "frostProtection"

# Error codes returned in {"error": {"code": ...}}
ERR_SESSION_EXPIRED = "USRSESSEXP"
ERR_BAD_CREDENTIALS = ("USRUNKN", "USRBADLOGIN", "VALINVLD", "INVALID")
ERR_LOCKED = ("USRLOCKED", "ACCLIMIT")
