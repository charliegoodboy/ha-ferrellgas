# Ferrellgas Home Assistant Integration

Custom HACS integration for Home Assistant that connects to MyFerrellgas and exposes propane tank telemetry as sensors.

## What It Does

- Authenticates against the Ferrellgas customer portal API.
- Polls account summary and order data on a configurable interval (default: hourly).
- Creates Home Assistant devices for each tank found on the account.
- Provides tank level, estimated gallons, delivery history, and cost tracking.
- Exposes low-propane binary sensor for alerting.
- Records long-term statistics for graphing usage over time.

## Sensors

### Tank Sensors
| Sensor | Description |
|--------|-------------|
| **Tank level** | Current estimated percentage full |
| **Estimated gallons** | Calculated gallons in tank |
| **Estimated propane value** | Dollar value of propane in tank (based on last delivery price) |
| **Gallons used since fill** | How many gallons consumed since last fill-up |
| **Estimated usage cost** | Dollar value of propane consumed since last fill |
| **Last delivery date** | When the most recent delivery occurred |
| **Last delivery gallons** | Gallons delivered in last order |
| **Price per gallon** | Unit price from last delivery |
| **Last delivery total** | Grand total of last delivery (incl. fees) |
| **Tank capacity** | Full tank capacity (diagnostic) |
| **Fill capacity** | Max fill capacity / 80% rule (diagnostic) |
| **Last reading date** | When the tank monitor last reported (diagnostic) |

### Account Sensors
| Sensor | Description |
|--------|-------------|
| **Account balance** | Current account balance |

### Binary Sensors
| Sensor | Description |
|--------|-------------|
| **Low propane** | On when tank is below configurable threshold (default: 20%) |

## Installation (HACS Custom Repository)

1. Open HACS in Home Assistant.
2. Go to **Integrations**.
3. Open the menu (three dots) and select **Custom repositories**.
4. Add this repository URL: `https://github.com/mattmarcin/ha-ferrellgas`
5. Category: **Integration**
6. Search for **Ferrellgas** and install.
7. Restart Home Assistant.

## Configuration

1. Go to **Settings > Devices & Services > Add Integration**.
2. Search for **Ferrellgas**.
3. Enter your MyFerrellgas username and password.
4. If you have multiple accounts, select which one to monitor.
5. Done! Sensors will appear under the Ferrellgas device.

### Options

After setup, click **Configure** on the integration to adjust:
- **Update interval** (5-1440 minutes, default: 60)
- **Low propane threshold** (1-100%, default: 20%)

## Example Automations

### Low Propane Alert
```yaml
automation:
  - alias: "Low Propane Notification"
    trigger:
      - platform: state
        entity_id: binary_sensor.ferrellgas_low_propane
        to: "on"
    action:
      - service: notify.mobile_app
        data:
          title: "Propane Low!"
          message: >
            Tank is at {{ states('sensor.ferrellgas_tank_level') }}%.
            Estimated {{ states('sensor.ferrellgas_estimated_gallons') }} gallons remaining
            (~${{ states('sensor.ferrellgas_estimated_value') }} worth).
```

### Weekly Usage Report
```yaml
automation:
  - alias: "Weekly Propane Report"
    trigger:
      - platform: time
        at: "09:00:00"
    condition:
      - condition: time
        weekday: mon
    action:
      - service: notify.mobile_app
        data:
          title: "Weekly Propane Update"
          message: >
            Tank: {{ states('sensor.ferrellgas_tank_level') }}%
            ({{ states('sensor.ferrellgas_estimated_gallons') }} gal).
            Used {{ states('sensor.ferrellgas_gallons_used_since_fill') }} gal
            since last fill (~${{ states('sensor.ferrellgas_estimated_usage_cost') }}).
            Last price: ${{ states('sensor.ferrellgas_last_price_per_gallon') }}/gal.
```

## API Details

This integration communicates with the Ferrellgas BFF API at `bff.myferrellgas.com`. No external Python dependencies are required beyond what Home Assistant provides.

### Endpoints Used
- `POST /api/Auth/Login/` — Authentication
- `GET /api/User/me` — Account discovery
- `GET /api/AccountSummary/{id}` — Tank telemetry
- `GET /api/Order/IP/{id}` — Order history per tank
- `GET /api/Order/{id}` — Order detail with line items and pricing

## License

MIT
