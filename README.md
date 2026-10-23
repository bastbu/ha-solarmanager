# Solar Manager Local (Home Assistant)

[![HACS](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://hacs.xyz/)
[![Open your Home Assistant instance and show the add repository dialog in HACS.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=bastbu&repository=ha-solarmanager&category=integration)
[![Open your Home Assistant instance and start setting up this integration.](https://my.home-assistant.io/badges/config_flow_start.svg)](https://my.home-assistant.io/redirect/config_flow_start/?domain=solar_manager_local)

Custom integration that reads data from a Solar Manager device via the local `/v2/point` endpoint.

### Gateway sensors

| Sensor | API field | Unit |
|---|---|---|
| PV production power | `pW` | W |
| Home consumption power | `cW` | W |
| PV energy produced total | `pWh` (accumulated) | kWh |

### Per-device sensors

Each device in the `devices` array is exposed as a separate Home Assistant device with:

| Sensor | API field | Unit |
|---|---|---|
| Power | `power` | W |
| Temperature | `temperature` | °C |
| Signal | `signal` | — |

Temperature is only created for devices that report it.

## Installation

1. Open HACS in Home Assistant.
2. Add this repository as a **Custom repository** (category: **Integration**).
3. Install **Solar Manager Local** and restart Home Assistant.

## Configuration

Add the integration and provide:

- **Base URL** — e.g. `http://192.168.1.20`
- **API key** — entered in a masked password field

To change these settings later, open **Settings > Devices & Services > Solar Manager Local**
and select **Reconfigure** from the integration entry's menu. The new settings are
validated before saving, then the integration reloads without removing its entities.
Leave the API key empty to keep the current key. Existing configurations that read
from `secrets.yaml` remain supported; entering a replacement key switches that entry
to direct storage without changing `secrets.yaml`.

API keys are stored in Home Assistant's configuration entry. Input masking does not
encrypt stored credentials; protect access to your configuration and backups.
