# Schluter DITRA-HEAT for Home Assistant

A custom integration for the Schluter DITRA-HEAT-E-RS1 Wi-Fi floor thermostat. It talks to the same cloud API the
schluterditraheat.com web app uses (Sinopé's Neviweb backend, `interface: "schluter"`), so it exposes everything the
web app does instead of the small subset HomeKit gives you.

## What you get (per thermostat)

| Platform | Entities |
|---|---|
| Climate | Off / Heat (manual) / Auto (follows the schedule); presets: frost protection, temporary override; heating vs idle action |
| Sensor | Floor temperature, room temperature, heating output %, power (W), energy today / yesterday / this month (kWh, works in the Energy dashboard), energy last hour*, Wi-Fi signal, error code, floor high/low and ambient limits* |
| Binary sensor | Heating, GFCI fault, device error |
| Select | Keypad lock, backlight, control mode (floor/ambient), display °F/°C, 12/24 h, secondary display, language*, floor probe type* |
| Number | Away setpoint, min/max setpoint, connected load (W), floor probe offset* |
| Switch | Early start, GFCI alert |
| Location | **Presence** select (Home/Away) for the whole location |

\* disabled by default; enable them on the device page if you want them.

Entities are only created for attributes your device actually reports.

Polling: device state every 60 s; device list and energy history every 15 min (the cloud only reports completed hours).

## Compared with HomeKit

HomeKit (local) gives: on/heat, setpoint, current temperature, display units, identify. Keep it if you want local
control as a fallback; otherwise you can remove the HomeKit Controller entry once this is working. Both can run side
by side — they'll show as two separate devices.

## Install

### HACS

1. HACS → ⋮ → **Custom repositories** → add `https://github.com/jmullally/ha-schluter-ditra` as type **Integration**.
2. Download **Schluter DITRA-HEAT**, then restart Home Assistant.
3. **Settings → Devices & services → Add integration → Schluter DITRA-HEAT**, sign in with your
   schluterditraheat.com email and password.

### Manual

1. Copy `custom_components/schluter_ditra/` into `/config/custom_components/` on your Home Assistant
   (File Editor add-on, Samba, or SSH).
2. Restart Home Assistant.
3. **Settings → Devices & services → Add integration → Schluter DITRA-HEAT**, sign in with your
   schluterditraheat.com email and password.

## Notes

- All temperatures are sent to and from the API in °C; Home Assistant converts to °F for display.
- Changing the setpoint while in Auto creates a temporary override (`autoBypass`) until the next schedule step.
  Selecting preset "None" while overriding returns to the schedule.
- Repeated failed logins can temporarily lock the account (`ACCLIMIT` / `USRLOCKED`); the integration will ask you to
  re-authenticate rather than retrying.
- Diagnostics download (device page → ⋮ → Download diagnostics) redacts your email, password and address.
