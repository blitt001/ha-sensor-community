"""Data coordinator for Sensor.Community integration."""
from __future__ import annotations

import asyncio
from datetime import datetime, timedelta
import logging
from typing import Any

import aiohttp

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from .const import (
    API_URL,
    CONF_DEBUG_MODE,
    CONF_SENSOR_HUMIDITY,
    CONF_SENSOR_ID,
    CONF_SENSOR_PM10,
    CONF_SENSOR_PM25,
    CONF_SENSOR_PRESSURE,
    CONF_SENSOR_TEMPERATURE,
    CONF_UPDATE_INTERVAL,
    DEFAULT_UPDATE_INTERVAL,
    DOMAIN,
    ENV_SENSORS,
    PIN_ENV,
    PIN_PM,
    PM_SENSORS,
    SOFTWARE_TYPE,
    VALUE_TYPE_MAP,
)

_LOGGER = logging.getLogger(__name__)

HTTP_TIMEOUT = 30


class SensorCommunityCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Coordinator for pushing data to Sensor.Community API."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        """Initialize the coordinator."""
        self.entry = entry
        self._sensor_id = entry.data[CONF_SENSOR_ID]
        self._session: aiohttp.ClientSession | None = None

        # Status tracking
        self.last_upload: datetime | None = None
        self.last_error: str | None = None
        self.upload_count: int = 0
        self.last_request_data: dict[str, Any] | None = None

        # Get update interval
        interval = entry.options.get(
            CONF_UPDATE_INTERVAL,
            entry.data.get(CONF_UPDATE_INTERVAL, DEFAULT_UPDATE_INTERVAL),
        )

        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=interval),
        )

    @property
    def debug_mode(self) -> bool:
        """Return whether debug mode is enabled."""
        return self.entry.options.get(
            CONF_DEBUG_MODE,
            self.entry.data.get(CONF_DEBUG_MODE, False),
        )

    @property
    def next_upload(self) -> datetime | None:
        """Return the next scheduled upload time."""
        if self.last_upload:
            return self.last_upload + self.update_interval
        return None

    def _has_pm_sensors(self) -> bool:
        """Check if any PM sensors are configured."""
        data = self.entry.data
        options = self.entry.options
        return any(options.get(field, data.get(field)) for field in PM_SENSORS)

    def _has_env_sensors(self) -> bool:
        """Check if any environmental sensors are configured."""
        data = self.entry.data
        options = self.entry.options
        return any(options.get(field, data.get(field)) for field in ENV_SENSORS)

    def _all_sensors_available(self) -> tuple[bool, list[str]]:
        """Check if all configured sensors are available.

        Returns a tuple of (all_available, list_of_unavailable_entities).
        """
        data = self.entry.data
        options = self.entry.options
        unavailable: list[str] = []

        all_fields = PM_SENSORS + ENV_SENSORS
        for field in all_fields:
            entity_id = options.get(field, data.get(field))
            if not entity_id:
                continue

            state = self.hass.states.get(entity_id)
            if state is None or state.state in ("unknown", "unavailable", None):
                unavailable.append(entity_id)

        return len(unavailable) == 0, unavailable

    async def _async_update_data(self) -> dict[str, Any]:
        """Push sensor data to Sensor.Community API."""
        try:
            # Check if all configured sensors are available
            all_available, unavailable = self._all_sensors_available()
            if not all_available:
                self.last_error = f"Sensors unavailable: {', '.join(unavailable)}"
                _LOGGER.warning(
                    "Skipping Sensor.Community upload - sensors unavailable: %s",
                    unavailable,
                )
                return self._get_status_data()

            if self._session is None:
                self._session = aiohttp.ClientSession()

            results: dict[str, Any] = {
                "pm_success": True,
                "env_success": True,
                "pm_response": None,
                "env_response": None,
            }

            # Push PM data if any PM sensors are configured
            if self._has_pm_sensors():
                success, response = await self._push_sensor_data(
                    pin=PIN_PM,
                    fields=PM_SENSORS,
                    data_type="pm",
                )
                results["pm_success"] = success
                results["pm_response"] = response

            # Push environmental data if any environmental sensors are configured
            if self._has_env_sensors():
                success, response = await self._push_sensor_data(
                    pin=PIN_ENV,
                    fields=ENV_SENSORS,
                    data_type="env",
                )
                results["env_success"] = success
                results["env_response"] = response

            # Update status
            if results["pm_success"] and results["env_success"]:
                self.last_upload = datetime.now()
                self.upload_count += 1
                self.last_error = None
            else:
                error_msgs = []
                if not results["pm_success"]:
                    error_msgs.append(f"PM: {results.get('pm_response', 'Unknown error')}")
                if not results["env_success"]:
                    error_msgs.append(f"ENV: {results.get('env_response', 'Unknown error')}")
                self.last_error = "; ".join(error_msgs) if error_msgs else None

            return self._get_status_data()

        except Exception as err:
            self.last_error = str(err)
            _LOGGER.exception("Error pushing data to Sensor.Community")
            return self._get_status_data()

    async def _push_sensor_data(
        self, pin: int, fields: list[str], data_type: str
    ) -> tuple[bool, str | None]:
        """Push sensor data to the API."""
        # Collect sensor values
        sensor_values = self._collect_sensor_data(fields)

        if not sensor_values:
            _LOGGER.debug("No sensor values to push for %s", data_type)
            return True, None  # Consider it success if nothing to push

        # Build payload
        payload = {
            "software_version": f"{SOFTWARE_TYPE}-1.0.0",
            "sensordatavalues": sensor_values,
        }

        # Build headers
        headers = {
            "Content-Type": "application/json",
            "X-Pin": str(pin),
            "X-Sensor": self._sensor_id,
            "User-Agent": f"{SOFTWARE_TYPE}/1.0.0",
        }

        if self.debug_mode:
            self.last_request_data = {
                "url": API_URL,
                "headers": {k: v for k, v in headers.items()},
                "payload": payload,
            }
            _LOGGER.debug(
                "Pushing %s data to Sensor.Community: %s",
                data_type,
                self.last_request_data,
            )

        try:
            async with asyncio.timeout(HTTP_TIMEOUT):
                async with self._session.post(
                    API_URL,
                    json=payload,
                    headers=headers,
                ) as response:
                    if response.status in (200, 201):
                        _LOGGER.debug(
                            "Successfully pushed %s data to Sensor.Community",
                            data_type,
                        )
                        return True, None
                    else:
                        error_text = await response.text()
                        _LOGGER.error(
                            "Failed to push %s data: %s - %s",
                            data_type,
                            response.status,
                            error_text,
                        )
                        return False, f"HTTP {response.status}: {error_text}"

        except asyncio.TimeoutError:
            _LOGGER.error("Timeout pushing %s data to Sensor.Community", data_type)
            return False, "Request timeout"
        except aiohttp.ClientError as err:
            _LOGGER.error("Network error pushing %s data: %s", data_type, err)
            return False, str(err)

    def _collect_sensor_data(self, fields: list[str]) -> list[dict[str, str]]:
        """Collect sensor data values from Home Assistant entities."""
        values: list[dict[str, str]] = []
        data = self.entry.data
        options = self.entry.options

        for field in fields:
            entity_id = options.get(field, data.get(field))
            if not entity_id:
                continue

            state = self.hass.states.get(entity_id)
            if state is None or state.state in ("unknown", "unavailable", None):
                _LOGGER.debug("Skipping %s: state is %s", entity_id, state)
                continue

            try:
                value = float(state.state)

                # Apply unit conversions
                value = self._convert_value(field, value, state)

                value_type = VALUE_TYPE_MAP.get(field)
                if value_type:
                    values.append({
                        "value_type": value_type,
                        "value": f"{value:.2f}",
                    })
            except (ValueError, TypeError) as err:
                _LOGGER.debug("Could not convert %s value: %s", entity_id, err)

        return values

    def _convert_value(self, field: str, value: float, state: Any) -> float:
        """Convert sensor value to the required unit."""
        unit = state.attributes.get("unit_of_measurement", "")

        # Temperature: convert Fahrenheit to Celsius
        if field == CONF_SENSOR_TEMPERATURE:
            if unit in ("°F", "F"):
                value = (value - 32) * 5 / 9
                _LOGGER.debug("Converted temperature from °F to °C: %.2f", value)

        # Pressure: convert hPa/mbar to Pa
        elif field == CONF_SENSOR_PRESSURE:
            if unit in ("hPa", "mbar", ""):
                value = value * 100
                _LOGGER.debug("Converted pressure from hPa to Pa: %.2f", value)
            elif unit == "inHg":
                value = value * 3386.39
                _LOGGER.debug("Converted pressure from inHg to Pa: %.2f", value)
            elif unit == "psi":
                value = value * 6894.76
                _LOGGER.debug("Converted pressure from psi to Pa: %.2f", value)
            # If already in Pa, no conversion needed

        # Humidity: ensure percentage (0-100)
        elif field == CONF_SENSOR_HUMIDITY:
            if value > 1 and value <= 100:
                pass  # Already in percentage
            elif value <= 1:
                value = value * 100  # Convert from decimal to percentage
                _LOGGER.debug("Converted humidity from decimal to percentage: %.2f", value)

        return value

    def _get_status_data(self) -> dict[str, Any]:
        """Get status data for the sensor."""
        data: dict[str, Any] = {
            "last_upload": self.last_upload.isoformat() if self.last_upload else None,
            "last_error": self.last_error,
            "upload_count": self.upload_count,
            "next_upload": self.next_upload.isoformat() if self.next_upload else None,
            "sensor_id": self._sensor_id,
        }

        if self.debug_mode and self.last_request_data:
            data["last_request"] = self.last_request_data

        return data

    async def async_shutdown(self) -> None:
        """Shutdown the coordinator and close the session."""
        if self._session:
            await self._session.close()
            self._session = None
