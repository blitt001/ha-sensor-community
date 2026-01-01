"""Constants for the Sensor.Community integration."""

DOMAIN = "sensor_community"

# API Configuration
API_URL = "http://api.sensor.community/v1/push-sensor-data/"
SOFTWARE_TYPE = "HomeAssistant-SensorCommunity"

# Update intervals
DEFAULT_UPDATE_INTERVAL = 150  # seconds (2.5 minutes as recommended by API)
MIN_UPDATE_INTERVAL = 60  # minimum 1 minute

# Configuration keys
CONF_SENSOR_ID = "sensor_id"
CONF_UPDATE_INTERVAL = "update_interval"
CONF_DEBUG_MODE = "debug_mode"

# PM sensor entities
CONF_SENSOR_PM25 = "sensor_pm25"
CONF_SENSOR_PM10 = "sensor_pm10"

# Environmental sensor entities
CONF_SENSOR_TEMPERATURE = "sensor_temperature"
CONF_SENSOR_HUMIDITY = "sensor_humidity"
CONF_SENSOR_PRESSURE = "sensor_pressure"

# X-Pin values - fixed categories for the API
PIN_PM = 1  # For all PM data
PIN_ENV = 11  # For all environmental data (temperature, humidity, pressure)

# Value type mappings for the API
VALUE_TYPE_MAP = {
    CONF_SENSOR_PM25: "P2",
    CONF_SENSOR_PM10: "P1",
    CONF_SENSOR_TEMPERATURE: "temperature",
    CONF_SENSOR_HUMIDITY: "humidity",
    CONF_SENSOR_PRESSURE: "pressure",
}

# Sensor groupings
PM_SENSORS = [CONF_SENSOR_PM25, CONF_SENSOR_PM10]
ENV_SENSORS = [CONF_SENSOR_TEMPERATURE, CONF_SENSOR_HUMIDITY, CONF_SENSOR_PRESSURE]
ALL_SENSORS = PM_SENSORS + ENV_SENSORS
