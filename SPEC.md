# Ferrellgas HACS Integration for Home Assistant

## Overview
Build a HACS-compatible custom integration for Home Assistant that connects to the Ferrellgas (MyFerrellgas) customer portal to monitor propane tank levels.

## API Details

### Base URL
`https://bff.myferrellgas.com`

### Authentication
**Login:** `POST /api/Auth/Login/`
```json
Request: {"username": "xxx", "password": "xxx", "changePwd": false, "newPassword": "", "ReturnUrl": ""}
Response: {
  "success": true,
  "error": null,
  "accessToken": "eyJ...",   // JWT, 1hr TTL
  "refreshToken": "eyJ...",  // JWE encrypted
  "expiresIn": 3600,
  "expireDate": "2026-02-17T09:56:43Z"
}
```

**Refresh:** `POST /Login/RefreshLogin`
(note: the base URL for this is the site base, not BFF — but the app uses `this.env.baseUrl + "/Login/RefreshLogin"`. Actually looking more carefully, `loginBaseURL` = `this.env.baseUrl + "/Login/"` where baseUrl = `https://myferrellgas.com`. So refresh endpoint is `https://myferrellgas.com/Login/RefreshLogin`)

Wait — let me clarify. The auth service URL is `this.envService.bffUrl + "/api/Auth"` = `https://bff.myferrellgas.com/api/Auth`. Login is at `/api/Auth/Login/`. But refresh uses `this.loginBaseURL + "RefreshLogin"` where `loginBaseURL = this.env.baseUrl + "/Login/"` = `https://myferrellgas.com/Login/`. So refresh is at `https://myferrellgas.com/Login/RefreshLogin`.

Actually, to keep it simple: just re-login with username/password when the token expires. The token lasts 1 hour and we only poll once per hour, so just login fresh each time. Much simpler than dealing with refresh token complexity.

### Get User Accounts
`GET /api/User/me`
```json
Headers: { "Authorization": "Bearer {accessToken}" }
Response: {
  "Accounts": ["238445840"],
  "ContactId": "003Ho000027Z1DqIAK",
  "FirstName": "Matthew",
  "LastName": "Marcin",
  "Email": "m@mattmarcin.com",
  "Phone": "6175151765",
  "HasNationalAccount": false
}
```

### Get Account Summary (includes tank data)
`GET /api/AccountSummary/{accountId}`
```json
Headers: { "Authorization": "Bearer {accessToken}" }
Response: {
  "Address1": "17158 Aileen Way",
  "Name": "Marcin,Matthew",
  "City": "Grass Valley",
  "AccountId": 238445840,
  "Postal": "95949-7201",
  "FinancialSummary": {
    "PaymentTerms": "NET30",
    "Balance": 0
  },
  "SiteSummary": [
    {
      "SiteId": "2007811199",
      "SiteName": "17158 Aileen Way-House",
      "Address1": "17158 Aileen Way",
      "City": "Grass Valley",
      "State": "CA",
      "IPSummary": [
        {
          "ProductDescription": "TANK - ABOVE GROUND 500 GALLON",
          "TankMonitor": true,
          "TankOwnership": "L",
          "InstalledProductId": "500000101445605",
          "ProductId": "TANK_500_GAL_ABOVE",
          "FullCapacity": 500,
          "FillCapacity": 400,
          "EstCurrPct": 57,
          "EstimatedPercentageDate": "2026-02-16T00:00:00",
          "MinimumFillQuantity": 200
        }
      ]
    }
  ]
}
```

## Integration Structure

```
ha-ferrellgas/
├── README.md
├── hacs.json
├── custom_components/
│   └── ferrellgas/
│       ├── __init__.py
│       ├── manifest.json
│       ├── config_flow.py
│       ├── const.py
│       ├── coordinator.py
│       ├── sensor.py
│       ├── api.py
│       └── strings.json
```

## Requirements

### Config Flow (UI Setup)
- Step 1: Username + Password fields
- Step 2 (if multiple accounts): Account selector
- Validates credentials on submit (actually calls the login API)
- Stores username + password in config entry (needed for re-auth since tokens expire)

### Data Coordinator
- Uses `DataUpdateCoordinator` with configurable scan interval (default: 1 hour)
- On each update: login fresh (POST /api/Auth/Login), then GET account summary
- No need for refresh token logic — just re-login each poll (simpler, token is 1hr and we poll hourly)
- Parse tank data from the response

### Sensors
For EACH tank found in the account (most users have 1, some could have multiple sites/tanks):

1. **Tank Level (%)** — `EstCurrPct`
   - `device_class: None` (no standard propane class)
   - `state_class: measurement`
   - `unit_of_measurement: "%"`
   - `icon: mdi:propane-tank`

2. **Estimated Gallons** — calculated: `EstCurrPct / 100 * FullCapacity`
   - `unit_of_measurement: "gal"`
   - `state_class: measurement`
   - `icon: mdi:propane-tank`

3. **Tank Capacity** — `FullCapacity`
   - Diagnostic entity
   - `unit_of_measurement: "gal"`

4. **Fill Capacity** — `FillCapacity` (80% rule max fill)
   - Diagnostic entity
   - `unit_of_measurement: "gal"`

5. **Last Reading Date** — `EstimatedPercentageDate`
   - `device_class: timestamp`
   - Diagnostic entity

6. **Account Balance** — `FinancialSummary.Balance`
   - `device_class: monetary`
   - `unit_of_measurement: "USD"`
   - `state_class: measurement`

### Device
Each tank should be a HA device:
- `name`: Site name + product description (e.g. "17158 Aileen Way-House")
- `manufacturer`: "Ferrellgas"
- `model`: Product description (e.g. "TANK - ABOVE GROUND 500 GALLON")
- `identifiers`: `{(DOMAIN, installed_product_id)}`

### Binary Sensor (optional but nice)
- **Low Propane** — True when `EstCurrPct` < 20% (or configurable threshold)
  - `device_class: problem`

### HACS Metadata
`hacs.json`:
```json
{
  "name": "Ferrellgas",
  "render_readme": true
}
```

`manifest.json`:
```json
{
  "domain": "ferrellgas",
  "name": "Ferrellgas",
  "codeowners": ["@mattmarcin"],
  "config_flow": true,
  "documentation": "https://github.com/mattmarcin/ha-ferrellgas",
  "iot_class": "cloud_polling",
  "issue_tracker": "https://github.com/mattmarcin/ha-ferrellgas/issues",
  "requirements": [],
  "version": "1.0.0"
}
```

## Key Design Notes
- NO external Python dependencies needed (just aiohttp which HA provides via `homeassistant.helpers.aiohttp_client`)
- Use `async_get_clientsession` from HA for HTTP calls
- Token management: just re-login each coordinator update cycle (simplest approach)
- Support multiple accounts and multiple tanks per account
- `state_class: measurement` on tank % and gallons so HA records long-term statistics automatically
- The graph comes for free from HA's history/statistics system

## README
Write a solid README.md with:
- What it does
- Screenshots placeholder
- Installation via HACS (custom repo)
- Configuration steps
- Available sensors
- Example automations (low propane alert)
