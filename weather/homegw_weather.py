"""
HomeGW platform that offers meteorological data.

https://github.com/dgomes/homeGW
"""
import asyncio
import logging
import json
import voluptuous as vol

from homeassistant.components.weather import (
    WeatherEntity)
from homeassistant.const import (
    TEMP_CELSIUS, CONF_NAME, STATE_UNKNOWN)
from homeassistant.core import callback
from homeassistant.components.weather import (
    PLATFORM_SCHEMA)
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.event import async_track_state_change
from homeassistant.helpers.restore_state import async_get_last_state
import sys
sys.path.append('/home/homeassistant/.homeassistant')
from custom_components.filter_helper import Filter, FILTER_OUTLIER


_LOGGER = logging.getLogger(__name__)

CONF_SERIAL_ENTITY = "serial_sensor"
DEFAULT_NAME = "HomeGW Weather Station"

ATTR_HOMEGW_DEV = 'dev'
ATTR_HOMEGW_TEMPERATURE = 'temp'
ATTR_HOMEGW_HUMIDITY = 'hum'
ATTR_HOMEGW_PRESSURE = 'pressure'
ATTR_HOMEGW_ID = 'id'
ATTR_HOMEGW_CHANNEL = 'ch'
ATTR_HOMEGW_BATTERY = 'batt'

VALUE_HOMEGW_DEV_WEATHER = 'weather'

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend({
    vol.Required(CONF_SERIAL_ENTITY): cv.entity_id,
    vol.Optional(CONF_NAME, default=DEFAULT_NAME): cv.string,
})


@asyncio.coroutine
def async_setup_platform(hass, config, async_add_devices, discovery_info=None):
    """Set up the homeGW weather."""
    name = config.get(CONF_NAME, DEFAULT_NAME)
    serial_sensor = config.get(CONF_SERIAL_ENTITY)

    async_add_devices([
        HomeGWWeather(hass, name, serial_sensor)
    ])


class HomeGWWeather(WeatherEntity):
    """Representation of a weather condition."""

    def __init__(self, hass, name, serial_sensor):
        """Initialize the HomeGW weather."""
        self._name = name

        self._temperature = None
        self._humidity = None
        self._pressure = None
        self._channel = self._id = self._battery = None

        async_track_state_change(hass, serial_sensor, self._sensor_changed)

    @asyncio.coroutine
    def async_added_to_hass(self):
        """Run when entity about to be added."""
        old_state = yield from async_get_last_state(self.hass, self.entity_id)
        if old_state is not None:
            if old_state.attributes.get(ATTR_HOMEGW_TEMPERATURE):
                self._temperature = float(
                    old_state.attributes[ATTR_HOMEGW_TEMPERATURE])
            if old_state.attributes.get(ATTR_HOMEGW_HUMIDITY):
                self._humidity = int(
                    old_state.attributes[ATTR_HOMEGW_HUMIDITY])
            if old_state.attributes.get(ATTR_HOMEGW_PRESSURE):
                self._pressure = int(
                    old_state.attributes[ATTR_HOMEGW_PRESSURE])

    @callback
    def _sensor_changed(self, entity_id, old_state, new_state):
        """Handle sensor state changes."""
        if new_state is None:
            return
        elif new_state.state == STATE_UNKNOWN:
            return

        try:
            payload = json.loads(new_state.state)
        except Exception:
            _LOGGER.warning("Could not process: %s", new_state.state)
            return

        if payload[ATTR_HOMEGW_DEV] != VALUE_HOMEGW_DEV_WEATHER:
            return

        self._temperature = float(payload[ATTR_HOMEGW_TEMPERATURE])
        self._humidity = int(payload[ATTR_HOMEGW_HUMIDITY])
        self._id = int(payload[ATTR_HOMEGW_ID])
        self._channel = int(payload[ATTR_HOMEGW_CHANNEL])
        self._battery = bool(payload[ATTR_HOMEGW_BATTERY])

        if payload.get(ATTR_HOMEGW_PRESSURE) is not None:
            self._pressure = int(payload[ATTR_HOMEGW_PRESSURE])

        self.schedule_update_ha_state()

    @property
    def name(self):
        """Return the name of the sensor."""
        return self._name

    @property
    def should_poll(self):
        """No polling needed for a demo weather condition."""
        return False

    @property
    @Filter(FILTER_OUTLIER,
            window_size=3, precision=2, entity="unnamed", radius=1.0)
    def temperature(self):
        """Return the temperature."""
        return self._temperature

    @property
    def temperature_unit(self):
        """Return the unit of measurement."""
        return TEMP_CELSIUS

    @property
    @Filter(FILTER_OUTLIER,
            window_size=3, precision=2, entity="unnamed", radius=1.0)
    def humidity(self):
        """Return the humidity."""
        return self._humidity

    @property
    def pressure(self):
        """Return the pressure."""
        return self._pressure

    @property
    def attribution(self):
        """Return the attribution."""
        return 'Retrieved through HomeGW'

    @property
    def device_state_attributes(self):
        """Return the state attributes."""
        attrs = super().state_attributes

        if self._channel is not None:
            attrs[ATTR_HOMEGW_CHANNEL] = self._channel
        if self._id is not None:
            attrs[ATTR_HOMEGW_ID] = self._id
        if self._battery is not None:
            attrs[ATTR_HOMEGW_BATTERY] = self._battery
        return attrs

    @property
    def condition(self):
        """Return condition."""
        if self._temperature is None:
            return STATE_UNKNOWN

        if self._humidity > 80:
            return 'rainy'
        return 'sunny'
