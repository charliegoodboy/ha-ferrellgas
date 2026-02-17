<p align="center">
  <img src="icon.png" alt="Ferrellgas Integration" width="128">
</p>

# Ferrellgas Home Assistant Integration

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-41BDF5.svg)](https://github.com/hacs/integration)
[![Open your Home Assistant instance and open a repository inside the Home Assistant Community Store.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=charliegoodboy&repository=ha-ferrellgas&category=integration)

Custom [HACS](https://hacs.xyz) integration for [Home Assistant](https://www.home-assistant.io/) that connects to the [MyFerrellgas](https://myferrellgas.com) customer portal and exposes propane tank telemetry, delivery history, and cost tracking as sensors.

## Features

- **Tank monitoring** — level %, estimated gallons, and dollar value of propane on hand
- **Delivery tracking** — date, gallons, price per gallon, and total cost of last delivery
- **Usage estimation** — gallons consumed and estimated cost since last fill
- **Low propane alert** — binary sensor with configurable threshold
- **Long-term statistics** — key sensors record history automatically for HA graphs
- **Multi-account / multi-tank** — supports accounts with multiple sites and tanks
- **Config flow** — full UI setup, no YAML needed

## Sensors

### Tank Sensors
| Sensor | Description |
|--------|-------------|
| **Tank level** | Current estimated percentage full |
| **Estimated gallons** | Calculated gallons in tank |
| **Estimated propane value** | Dollar value of propane in tank (at last delivery price) |
| **Gallons used since fill** | Gallons consumed since last fill-up |
| **Estimated usage cost** | Dollar value of propane consumed since last fill |
| **Last delivery date** | When the most recent delivery occurred |
| **Last delivery gallons** | Gallons delivered in last order |
| **Price per gallon** | Unit price from last delivery |
| **Last delivery total** | Grand total of last delivery (incl. surcharges and fees) |
| **Tank capacity** | Full tank capacity in gallons *(diagnostic)* |
| **Fill capacity** | Max fill capacity / 80% rule *(diagnostic)* |
| **Last reading date** | When the tank monitor last reported *(diagnostic)* |

### Account Sensors
| Sensor | Description |
|--------|-------------|
| **Account balance** | Current account balance |

### Binary Sensors
| Sensor | Description |
|--------|-------------|
| **Low propane** | On when tank level is below threshold (default: 20%) |

## Requirements

- A **Ferrellgas** propane account with [MyFerrellgas](https://myferrellgas.com) portal access
- **Home Assistant** 2024.4 or newer
- **[HACS](https://hacs.xyz)** installed in your Home Assistant instance

## Installation

### Option 1: HACS (Recommended)

1. Open **HACS** in Home Assistant
2. Click the **three-dot menu** (top right) → **Custom repositories**
3. Paste the repository URL:
   ```
   https://github.com/charliegoodboy/ha-ferrellgas
   ```
4. Select category: **Integration**
5. Click **Add**
6. Search for **Ferrellgas** in HACS and click **Download**
7. **Restart Home Assistant**

### Option 2: Manual

1. Download or clone this repository
2. Copy `custom_components/ferrellgas/` into your Home Assistant `config/custom_components/` directory
3. Restart Home Assistant

## Setup

1. Go to **Settings → Devices & Services → Add Integration**
2. Search for **Ferrellgas**
3. Enter your MyFerrellgas username and password
4. If you have multiple accounts, select which one to monitor
5. Done — sensors appear automatically under the new Ferrellgas device

### Options

After setup, click **Configure** on the integration to adjust:

| Option | Range | Default |
|--------|-------|---------|
| Update interval | 5 – 1440 minutes | 60 min |
| Low propane threshold | 1 – 100% | 20% |

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

## How It Works

This integration communicates with the Ferrellgas BFF API (`bff.myferrellgas.com`) — the same backend that powers the MyFerrellgas web portal. It authenticates with your username and password, then polls for tank data and order history on each update cycle.

**No external Python dependencies** are required. The integration uses `aiohttp` which Home Assistant provides natively.

### API Endpoints
| Endpoint | Purpose |
|----------|---------|
| `POST /api/Auth/Login/` | Authentication |
| `GET /api/User/me` | Account discovery |
| `GET /api/AccountSummary/{id}` | Tank telemetry and site info |
| `GET /api/Order/IP/{id}` | Order history per tank |
| `GET /api/Order/{id}` | Order detail with line items and pricing |

## Troubleshooting

- **"Invalid username or password"** — Make sure you can log in at [myferrellgas.com](https://myferrellgas.com). If this is your first login since July 2025, you may need to [reset your password](https://myferrellgas.com/forgotpassword) first.
- **Sensors show "unavailable"** — Check your HA logs for connection errors. The integration re-authenticates on each poll, so temporary API outages will recover automatically.
- **Delivery sensors are empty** — These require at least one delivery order in your Ferrellgas account history (goes back 13 months).

## License

MIT

## Contributing

Issues and pull requests welcome at [github.com/charliegoodboy/ha-ferrellgas](https://github.com/charliegoodboy/ha-ferrellgas).
