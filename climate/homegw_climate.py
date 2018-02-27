"""
HomeGW platform that offers meteorological data.

https://github.com/dgomes/homeGW
"""
import asyncio
import logging
import json
import voluptuous as vol

from homeassistant.components.climate import (
    ClimateDevice, SUPPORT_TARGET_HUMIDITY_LOW,
    ATTR_CURRENT_HUMIDITY, ATTR_CURRENT_TEMPERATURE,
    PLATFORM_SCHEMA, STATE_UNKNOWN)
from homeassistant.const import (
    TEMP_CELSIUS, CONF_NAME, STATE_ON)
from homeassistant.core import callback
from homeassistant.helpers.event import async_track_state_change
from homeassistant.helpers.restore_state import async_get_last_state
import homeassistant.helpers.config_validation as cv
from ..filter_helper import Filter, FILTER_OUTLIER

_LOGGER = logging.getLogger(__name__)

SUPPORT_FLAGS = SUPPORT_TARGET_HUMIDITY_LOW

CONF_SERIAL_ENTITY = 'serial_sensor'
CONF_HEATING_ENTITY = 'heating_sensor'
CONF_DEV_CHANNEL = 'channel'
CONF_TARGET_TEMP = 'target_temp'

ATTR_HOMEGW_DEV = 'dev'
ATTR_HOMEGW_TEMPERATURE = 'temp'
ATTR_HOMEGW_HUMIDITY = 'hum'
ATTR_HOMEGW_ID = 'id'
ATTR_HOMEGW_CHANNEL = 'ch'
ATTR_HOMEGW_BATTERY = 'batt'

DEFAULT_NAME = "HomeGW thermostat"

VALUE_HOMEGW_DEV_DIGOO = 'digoo'

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend({
    vol.Required(CONF_SERIAL_ENTITY): cv.entity_id,
    vol.Required(CONF_DEV_CHANNEL): cv.positive_int,
    vol.Optional(CONF_HEATING_ENTITY): cv.entity_id,
    vol.Optional(CONF_NAME, default=DEFAULT_NAME): cv.string,
    vol.Optional(CONF_TARGET_TEMP): vol.Coerce(float),
})


@asyncio.coroutine
def async_setup_platform(hass, config, async_add_devices, discovery_info=None):
    """Set up homeGW climate devices."""
    serial_sensor = config[CONF_SERIAL_ENTITY]
    dev_channel = config[CONF_DEV_CHANNEL]
    heating_sensor = config.get(CONF_HEATING_ENTITY)
    name = config.get(CONF_NAME, DEFAULT_NAME)
    target_temp = config.get(CONF_TARGET_TEMP)

    async_add_devices([
        HomeGWClimate(hass, name, serial_sensor,
                      heating_sensor, dev_channel, target_temp)
    ])


class HomeGWClimate(ClimateDevice):
    """Representation of a demo climate device."""

    def __init__(self, hass, name, serial_sensor,
                 heating_sensor, dev_channel, target_temp):
        """Initialize the climate device."""
        self._name = name
        self._channel = dev_channel
        self._id = None
        self._battery = None
        self._unit_of_measurement = TEMP_CELSIUS
        self._support_flags = SUPPORT_FLAGS

        self._current_operation = 'idle'
        self._current_temperature = None
        self._current_humidity = None
        self._temperature = target_temp
        self._humidity = None
        self._target_humidity = 50

        async_track_state_change(hass, serial_sensor, self._sensor_changed)
        async_track_state_change(hass, heating_sensor, self._heating_changed)

    @asyncio.coroutine
    def async_added_to_hass(self):
        """Run when entity about to be added."""
        old_state = yield from async_get_last_state(self.hass, self.entity_id)
        if old_state is not None:
            _LOGGER.debug("Loading %s old_state: %s",
                          self.entity_id, old_state)
            if old_state.attributes.get(ATTR_CURRENT_TEMPERATURE):
                self._current_temperature = float(
                    old_state.attributes[ATTR_CURRENT_TEMPERATURE])
            if old_state.attributes.get(ATTR_CURRENT_HUMIDITY):
                self._current_humidity = int(
                    old_state.attributes[ATTR_CURRENT_HUMIDITY])

    @callback
    def _heating_changed(self, entity_id, old_state, new_state):
        """Handle sensor state changes."""
        if new_state is None:
            return
        elif new_state.state == STATE_UNKNOWN:
            return

        if new_state.state == STATE_ON:
            self._current_operation = 'heat'
        else:
            self._current_operation = 'idle'
        self.schedule_update_ha_state()

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

        if payload[ATTR_HOMEGW_DEV] != VALUE_HOMEGW_DEV_DIGOO:
            return
        if payload[ATTR_HOMEGW_CHANNEL] != self._channel:
            return

        self._current_temperature = float(payload[ATTR_HOMEGW_TEMPERATURE])
        self._current_humidity = int(payload[ATTR_HOMEGW_HUMIDITY])
        self._id = int(payload[ATTR_HOMEGW_ID])
        self._channel = int(payload[ATTR_HOMEGW_CHANNEL])
        self._battery = bool(payload[ATTR_HOMEGW_BATTERY])

        self.schedule_update_ha_state()

    @property
    def supported_features(self):
        """Return the list of supported features."""
        return self._support_flags

    @property
    def should_poll(self):
        """Return the polling state."""
        return False

    @property
    def name(self):
        """Return the name of the climate device."""
        return self._name

    @property
    def temperature_unit(self):
        """Return the unit of measurement."""
        return self._unit_of_measurement

    @Filter(FILTER_LOWPASS,
            window_size=1, precision=0.25, entity="unnamed",time_constant=4)
    @Filter(FILTER_OUTLIER,
            window_size=3, precision=2, entity="unnamed", radius=2.0)
    def filter_current_temperature(self):
        """Return the filtered current temperature."""
        return self._current_temperature

    @property
    def current_temperature(self):
        """Return the current temperature."""
        return round(filter_current_temperature() / 0.25) * 0.25

    @Filter(FILTER_LOWPASS,
            window_size=1, precision=0.25, entity="unnamed",time_constant=4)
    @Filter(FILTER_OUTLIER,
            window_size=3, precision=2, entity="unnamed", radius=2.0)
    def filter_current_humidity(self):
        """Return the filtered current humidity."""
        return self._current_humidity

    @property
    def current_humidity(self):
        """Return the current humidity."""
        return round(filter_current_humidity() / 0.25) * 0.25

    @property
    def current_operation(self):
        """Return current operation ie. heat, cool, idle."""
        return self._current_operation

    @property
    def device_state_attributes(self):
        """Return the state attributes."""
        attrs = {
            ATTR_CURRENT_TEMPERATURE: self.current_temperature,
            ATTR_CURRENT_HUMIDITY: self.current_humidity,
        }
        if self._channel is not None:
            attrs[ATTR_HOMEGW_CHANNEL] = self._channel
        if self._id is not None:
            attrs[ATTR_HOMEGW_ID] = self._id
        if self._battery is not None:
            attrs[ATTR_HOMEGW_BATTERY] = self._battery
        return attrs
