# Solar Manager Local (Home Assistant)

[![HACS](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://hacs.xyz/)
[![Open your Home Assistant instance and show the add repository dialog in HACS.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=bastbu&repository=ha-solarmanager&category=integration)
[![Open your Home Assistant instance and start setting up this integration.](https://my.home-assistant.io/badges/config_flow_start.svg)](https://my.home-assistant.io/redirect/config_flow_start/?domain=solar_manager_local)

This custom integration reads Solar Manager data from the local `/v2/point` endpoint and exposes three sensors:

- `Current power production` → `pW` (W)
- `Current power consumption` → `cW` (W)
- `Energy produced` → `pWh` (shown as kWh in Home Assistant)

Default polling interval is **7 seconds**. If the Home Assistant integration misses polling during a certain window, we will get erroneous total produced energy, which we do not prevent at the moment.

## Installation

### Via HACS (Custom Repository)

1. Open HACS in Home Assistant.
2. Add this repository as a **Custom repository** with category **Integration**.
3. Install **Solar Manager Local**.
4. Restart Home Assistant.

## Secrets

Set the API key in your `secrets.yaml`:

```yaml
solar_manager_api_key: "YOUR_API_KEY"
```

In the integration setup, set:

- `Base URL` (for example `http://192.168.1.20`)
- `Secret name for API key` (default: `solar_manager_api_key`)

## Expected API fields

The integration expects `/v2/point` to return a JSON object containing at least:

- `cW`, `pW`, `pWh`

Additional API fields are ignored.
