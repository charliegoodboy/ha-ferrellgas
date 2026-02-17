# Ferrellgas Home Assistant Integration

Custom HACS integration for Home Assistant that connects to MyFerrellgas and exposes propane tank telemetry as sensors.

## What It Does

- Authenticates against the Ferrellgas customer portal API.
- Polls account summary data on a configurable interval (default: hourly).
- Creates Home Assistant devices for each tank found on the account.
- Provides tank level and estimated gallons for dashboards, automations, and long-term statistics.
- Exposes low-propane binary sensor for alerting.

## Screenshots

- Dashboard card placeholder
- Entity list placeholder
- Automation example placeholder

## Installation (HACS Custom Repository)

1. Open HACS in Home Assistant.
2. Go to `Integrations`.
3. Open the menu and select `Custom repositories`.
4. Add this repository URL.
5. Category: `Integration`.
6. Search for `Ferrellgas` and install.
7. Restart Home Assistant.

## Configuration

1. Go to `Settings` -> `Devices & Services`.
2. Click `Add Integration`.
3. Search for `Ferrellgas`.
4. Enter your MyFerrellgas username and password.
5. If multiple accounts are available, choose the account to monitor.
6. Optional: adjust polling interval and low propane threshold in integration options.

## Entities

Per tank device:

- `Tank level` (`%`, measurement)
- `Estimated gallons` (`gal`, measurement)
- `Tank capacity` (`gal`, diagnostic)
- `Fill capacity` (`gal`, diagnostic)
- `Last reading date` (`timestamp`, diagnostic)
- `Low propane` (`binary_sensor`, on when tank % is below threshold)

Account-level:

- `Account balance` (`USD`, monetary)

## Example Automation: Low Propane Alert

```yaml
alias: Ferrellgas Low Propane Alert
trigger:
  - platform: state
    entity_id: binary_sensor.home_tank_low_propane
    to: "on"
action:
  - service: notify.mobile_app_phone
    data:
      title: Propane Alert
      message: Propane level is below threshold. Schedule a refill.
mode: single
```

## Notes

- The integration logs in fresh each polling cycle; refresh token flow is intentionally not used.
- No external Python dependencies are required.
