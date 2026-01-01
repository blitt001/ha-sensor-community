"""Config flow for Sensor.Community integration."""
from __future__ import annotations

import logging
import re
from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers import selector

from .const import (
    ALL_SENSORS,
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
    MIN_UPDATE_INTERVAL,
)

_LOGGER = logging.getLogger(__name__)

SENSOR_ID_PATTERN = re.compile(r"^[a-zA-Z0-9]+-[a-zA-Z0-9]+$")


def validate_sensor_id(sensor_id: str) -> bool:
    """Validate the sensor ID format."""
    return bool(SENSOR_ID_PATTERN.match(sensor_id))


class SensorCommunityConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Sensor.Community."""

    VERSION = 1

    def __init__(self) -> None:
        """Initialize the config flow."""
        self._data: dict[str, Any] = {}

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step - sensor ID configuration."""
        errors: dict[str, str] = {}

        if user_input is not None:
            sensor_id = user_input[CONF_SENSOR_ID].strip()

            if not validate_sensor_id(sensor_id):
                errors["base"] = "invalid_sensor_id"
            else:
                # Check if already configured
                await self.async_set_unique_id(sensor_id)
                self._abort_if_unique_id_configured()

                self._data[CONF_SENSOR_ID] = sensor_id
                return await self.async_step_sensors()

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_SENSOR_ID): str,
                }
            ),
            errors=errors,
            description_placeholders={
                "example": "esp8266-12345678",
            },
        )

    async def async_step_sensors(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle sensor entity mapping step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            # Check that at least one sensor is configured
            has_sensor = any(user_input.get(field) for field in ALL_SENSORS)
            if not has_sensor:
                errors["base"] = "no_sensor_configured"
            else:
                # Store the sensor mappings
                for field in ALL_SENSORS:
                    if user_input.get(field):
                        self._data[field] = user_input[field]

                return await self.async_step_options()

        return self.async_show_form(
            step_id="sensors",
            data_schema=vol.Schema(
                {
                    vol.Optional(CONF_SENSOR_PM25): selector.EntitySelector(
                        selector.EntitySelectorConfig(domain="sensor")
                    ),
                    vol.Optional(CONF_SENSOR_PM10): selector.EntitySelector(
                        selector.EntitySelectorConfig(domain="sensor")
                    ),
                    vol.Optional(CONF_SENSOR_TEMPERATURE): selector.EntitySelector(
                        selector.EntitySelectorConfig(domain="sensor")
                    ),
                    vol.Optional(CONF_SENSOR_HUMIDITY): selector.EntitySelector(
                        selector.EntitySelectorConfig(domain="sensor")
                    ),
                    vol.Optional(CONF_SENSOR_PRESSURE): selector.EntitySelector(
                        selector.EntitySelectorConfig(domain="sensor")
                    ),
                }
            ),
            errors=errors,
        )

    async def async_step_options(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle options configuration step."""
        if user_input is not None:
            self._data[CONF_UPDATE_INTERVAL] = user_input.get(
                CONF_UPDATE_INTERVAL, DEFAULT_UPDATE_INTERVAL
            )
            self._data[CONF_DEBUG_MODE] = user_input.get(CONF_DEBUG_MODE, False)

            return self.async_create_entry(
                title=f"Sensor.Community ({self._data[CONF_SENSOR_ID]})",
                data=self._data,
            )

        return self.async_show_form(
            step_id="options",
            data_schema=vol.Schema(
                {
                    vol.Optional(
                        CONF_UPDATE_INTERVAL,
                        default=DEFAULT_UPDATE_INTERVAL,
                    ): selector.NumberSelector(
                        selector.NumberSelectorConfig(
                            min=MIN_UPDATE_INTERVAL,
                            max=600,
                            step=10,
                            unit_of_measurement="seconds",
                            mode=selector.NumberSelectorMode.BOX,
                        )
                    ),
                    vol.Optional(CONF_DEBUG_MODE, default=False): bool,
                }
            ),
        )

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> SensorCommunityOptionsFlow:
        """Get the options flow for this handler."""
        return SensorCommunityOptionsFlow()


class SensorCommunityOptionsFlow(config_entries.OptionsFlow):
    """Handle options flow for Sensor.Community."""

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle options flow."""
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        # Get current values - merge data and options
        current_data = {**self.config_entry.data, **self.config_entry.options}

        current_interval = current_data.get(CONF_UPDATE_INTERVAL, DEFAULT_UPDATE_INTERVAL)
        current_debug = current_data.get(CONF_DEBUG_MODE, False)

        # Create entity selector
        entity_selector = selector.EntitySelector(
            selector.EntitySelectorConfig(domain="sensor")
        )

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Optional(
                        CONF_SENSOR_PM25,
                        description={"suggested_value": current_data.get(CONF_SENSOR_PM25)},
                    ): entity_selector,
                    vol.Optional(
                        CONF_SENSOR_PM10,
                        description={"suggested_value": current_data.get(CONF_SENSOR_PM10)},
                    ): entity_selector,
                    vol.Optional(
                        CONF_SENSOR_TEMPERATURE,
                        description={"suggested_value": current_data.get(CONF_SENSOR_TEMPERATURE)},
                    ): entity_selector,
                    vol.Optional(
                        CONF_SENSOR_HUMIDITY,
                        description={"suggested_value": current_data.get(CONF_SENSOR_HUMIDITY)},
                    ): entity_selector,
                    vol.Optional(
                        CONF_SENSOR_PRESSURE,
                        description={"suggested_value": current_data.get(CONF_SENSOR_PRESSURE)},
                    ): entity_selector,
                    vol.Optional(CONF_UPDATE_INTERVAL, default=current_interval): selector.NumberSelector(
                        selector.NumberSelectorConfig(
                            min=MIN_UPDATE_INTERVAL,
                            max=600,
                            step=10,
                            unit_of_measurement="seconds",
                            mode=selector.NumberSelectorMode.BOX,
                        )
                    ),
                    vol.Optional(CONF_DEBUG_MODE, default=current_debug): bool,
                }
            ),
        )
