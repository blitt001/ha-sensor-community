# Sensor.Community Uploader for Home Assistant

<!-- Badges -->
[![HACS Custom](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://github.com/hacs/integration)
[![GitHub Release](https://img.shields.io/github/v/release/blitt001/ha-sensor-community)](https://github.com/blitt001/ha-sensor-community/releases)
[![GitHub License](https://img.shields.io/github/license/blitt001/ha-sensor-community)](LICENSE)
[![GitHub Downloads](https://img.shields.io/github/downloads/blitt001/ha-sensor-community/total)](https://github.com/blitt001/ha-sensor-community/releases)
[![GitHub Stars](https://img.shields.io/github/stars/blitt001/ha-sensor-community)](https://github.com/blitt001/ha-sensor-community/stargazers)

<!-- TODO: Add logo/banner image
![Sensor.Community Logo](images/logo.png)
-->

**Upload** your weather station and air quality data from Home Assistant to the [Sensor.Community](https://sensor.community/) citizen science network (formerly Luftdaten).

This integration allows you to contribute measurements from your personal weather station or environmental sensors (temperature, humidity, pressure, PM2.5, PM10) to the global Sensor.Community network - without needing dedicated hardware like an ESP8266.

> **Note:** This integration **uploads** data TO Sensor.Community. It is different from the built-in Home Assistant `luftdaten` integration which only **reads** data FROM the network.

<!-- TODO: Add screenshot of the integration
## Screenshot

![Configuration Flow](images/screenshot.png)
-->

## Features

- **Simple UI Configuration** - Easy setup through Home Assistant's integration UI
- **Direct Sensor Mapping** - Just map your HA sensors, no hardware type selection needed
- **Automatic Uploads** - Configurable interval-based data pushing (default: 2.5 minutes)
- **Status Monitoring** - Track upload status, errors, and upload history
- **Debug Mode** - View exact API requests for troubleshooting

## Supported Measurements

| Measurement | API Value Type | X-Pin Header |
|-------------|----------------|--------------|
| PM2.5 | P2 | 1 |
| PM10 | P1 | 1 |
| Temperature | temperature | 11 |
| Humidity | humidity | 11 |
| Pressure | pressure | 11 |

The integration automatically sends PM data with `X-Pin: 1` and environmental data with `X-Pin: 11`, matching the standard Sensor.Community API format.

## Installation

### HACS (Recommended)

[![Open your Home Assistant instance and open a repository inside the Home Assistant Community Store.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=blitt001&repo=ha-sensor-community&category=integration)

Click the button above, or manually:

1. Open HACS in Home Assistant
2. Go to **Integrations**
3. Click the three dots menu and select **Custom repositories**
4. Add this repository URL: `https://github.com/blitt001/ha-sensor-community`
5. Select **Integration** as the category
6. Click **Install**
7. Restart Home Assistant

### Manual Installation

1. Download the latest release from GitHub
2. Copy the `custom_components/sensor_community` folder to your Home Assistant's `custom_components` directory
3. Restart Home Assistant

## Configuration

[![Open your Home Assistant instance and start setting up a new integration.](https://my.home-assistant.io/badges/config_flow_start.svg)](https://my.home-assistant.io/redirect/config_flow_start/?domain=sensor_community)

Click the button above, or manually:

1. Go to **Settings** > **Devices & Services**
2. Click **Add Integration**
3. Search for **Sensor.Community**
4. Follow the setup wizard:
   - Enter your Sensor.Community sensor ID (e.g., `esp8266-12345678`)
   - Map your Home Assistant sensor entities
   - Configure update interval (recommended: 150 seconds)

## Getting a Sensor ID

If you don't have a sensor ID yet:

1. Go to [devices.sensor.community](https://devices.sensor.community/)
2. Register your device
3. You'll receive a sensor ID in the format `esp8266-XXXXXXXX` or similar

## How It Works

The integration makes up to two API calls per update cycle:

1. **PM Data** (`X-Pin: 1`) - Sends PM2.5 and PM10 values
2. **Environmental Data** (`X-Pin: 11`) - Sends temperature, humidity, and pressure values

This matches the standard Sensor.Community API format used by devices like the popular ESP8266-based air quality sensors.

## Status Sensor

The integration creates a status sensor with `device_class: enum`. The entity ID is based on your sensor ID, for example: `sensor.sensor_community_esp8266_12345678_status`.

### Sensor States

| State | Description |
|-------|-------------|
| `pending` | Integration started, waiting for first upload |
| `ok` | Last upload was successful |
| `error` | Upload failed or sensors unavailable |

### Attributes

| Attribute | Description |
|-----------|-------------|
| `sensor_id` | Your Sensor.Community ID |
| `upload_count` | Number of successful uploads |
| `last_upload` | Timestamp of last successful upload |
| `next_upload` | Timestamp of next scheduled upload |
| `last_error` | Last error message (if any) |
| `last_request` | Request details (debug mode only) |

## Logging

The integration logs important events to the Home Assistant log:

| Level | Event |
|-------|-------|
| `WARNING` | Sensors unavailable, upload skipped |
| `ERROR` | HTTP error (4xx/5xx response) |
| `ERROR` | Request timeout |
| `ERROR` | Network connection error |

Example log entries:
```
WARNING - Skipping Sensor.Community upload - sensors unavailable: ['sensor.bme280_temperature']
ERROR - Failed to push pm data: 500 - Internal Server Error
ERROR - Timeout pushing env data to Sensor.Community
```

### Enable Debug Logging

To enable detailed debug logging, add the following to your `configuration.yaml`:

```yaml
logger:
  default: info
  logs:
    custom_components.sensor_community: debug
```

Restart Home Assistant after adding this configuration.

## Automations

You can create automations based on the status sensor state changes.

### Example: Send notification on error

```yaml
alias: Notify Sensor.Community Upload Error
description: Send notification when upload fails
triggers:
  - trigger: state
    entity_id: sensor.sensor_community_esp8266_12345678_status  # Replace with your entity ID
    to: "error"
conditions: []
actions:
  - action: notify.notify
    data:
      title: "Sensor.Community Upload Failed"
      message: "Error: {{ state_attr('sensor.sensor_community_esp8266_12345678_status', 'last_error') }}"
```

### Example: Send email when sensors become unavailable

```yaml
alias: Email on Sensor.Community Sensor Unavailable
triggers:
  - trigger: state
    entity_id: sensor.sensor_community_esp8266_12345678_status  # Replace with your entity ID
    to: "error"
conditions:
  - condition: template
    value_template: >
      {{ 'unavailable' in state_attr('sensor.sensor_community_esp8266_12345678_status', 'last_error') }}
actions:
  - action: notify.email
    data:
      title: "Air Quality Sensors Unavailable"
      message: |
        One or more sensors are unavailable.

        Error: {{ state_attr('sensor.sensor_community_esp8266_12345678_status', 'last_error') }}

        Please check your sensor connections.
```

### Example: Log when upload recovers

```yaml
alias: Log Sensor.Community Recovery
triggers:
  - trigger: state
    entity_id: sensor.sensor_community_esp8266_12345678_status  # Replace with your entity ID
    from: "error"
    to: "ok"
actions:
  - action: system_log.write
    data:
      message: "Sensor.Community upload recovered after error"
      level: info
```

## Unit Conversions

The integration automatically detects and converts units based on the sensor's `unit_of_measurement` attribute:

| Measurement | Input Unit | Output Unit | Conversion |
|-------------|------------|-------------|------------|
| Temperature | °F | °C | (°F - 32) × 5/9 |
| Temperature | °C | °C | No conversion |
| Pressure | hPa, mbar | Pa | × 100 |
| Pressure | inHg | Pa | × 3386.39 |
| Pressure | psi | Pa | × 6894.76 |
| Pressure | Pa | Pa | No conversion |
| Humidity | 0-1 (decimal) | % | × 100 |
| Humidity | 0-100 (%) | % | No conversion |

## Troubleshooting

### Data not appearing on Sensor.Community

1. Check the status sensor for errors
2. Enable debug mode in the integration options to see exact API requests
3. Verify your sensor ID is correct and registered
4. Ensure your sensors have valid (non-unavailable) readings

### Connection Errors

The API endpoint uses HTTP (not HTTPS) as recommended by Sensor.Community for reliability.

### Invalid Sensor ID

The sensor ID must be in the format `prefix-id`, for example:
- `esp8266-12345678`
- `raspi-abcdef123456`

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

<!-- TODO: Add support/donation link
## Support

If you find this integration useful, consider buying me a coffee:

[![Buy Me A Coffee](https://img.shields.io/badge/Buy%20Me%20A%20Coffee-donate-yellow.svg)](https://buymeacoffee.com/YOUR_USERNAME)
-->
