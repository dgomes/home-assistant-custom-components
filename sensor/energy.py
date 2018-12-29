"""
Energy meter with multiple tariff periods.

For more details about this platform, please refer to the documentation at
https://home-assistant.io/components/sensor.energy/
"""
import logging

import voluptuous as vol

import homeassistant.util.dt as dt_util
import homeassistant.helpers.config_validation as cv
from homeassistant.components.sensor import (DOMAIN, PLATFORM_SCHEMA)
from homeassistant.const import (
    CONF_NAME, ATTR_UNIT_OF_MEASUREMENT, ATTR_ENTITY_ID)
from homeassistant.core import callback
from homeassistant.helpers.event import async_track_state_change
from homeassistant.helpers.restore_state import RestoreEntity

_LOGGER = logging.getLogger(__name__)

ATTR_SOURCE_ID = 'source'
ATTR_PERIODICITY = 'periodicity'  # TODO reset meter periodically
ATTR_LAST_RESET = 'last reset'

SERVICE_RESET = 'reset'

SERVICE_RESET_SCHEMA = vol.Schema({
    vol.Required(ATTR_ENTITY_ID): cv.entity_id,
})

CONF_SOURCE_SENSOR = 'source_sensor'
CONF_ROUND_DIGITS = 'round'
CONF_TARIFF = 'tariff'

UNIT_WATTS = "W"
UNIT_KILOWATTS = "kW"
UNIT_KILOWATTS_HOUR = "kWh"

UNIT_OF_MEASUREMENT = UNIT_KILOWATTS_HOUR
ICON = 'mdi:counter'

DEFAULT_ROUND = 3

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend({
    vol.Optional(CONF_NAME): cv.string,
    vol.Required(CONF_SOURCE_SENSOR): cv.entity_id,
    vol.Optional(CONF_TARIFF): cv.entity_id,
    vol.Optional(CONF_ROUND_DIGITS, default=DEFAULT_ROUND): vol.Coerce(int),
})


async def async_setup_platform(hass, config, async_add_entities,
                               discovery_info=None):
    """Set up the energy sensor."""
    meter = EnergySensor(hass, config[CONF_SOURCE_SENSOR],
                         config.get(CONF_TARIFF),
                         config.get(CONF_NAME),
                         config[CONF_ROUND_DIGITS])

    async_add_entities([meter])

    async def async_reset_meter(service):
        if service.data.get(ATTR_ENTITY_ID) == meter.entity_id:
            await meter.async_reset()

    hass.services.async_register(DOMAIN, SERVICE_RESET,
                                 async_reset_meter,
                                 schema=SERVICE_RESET_SCHEMA)

    return True
 

class EnergySensor(RestoreEntity):
    """Representation of an energy sensor."""

    def __init__(self, hass, source_entity, tariff_entity, name, round_digits):
        """Initialize the min/max sensor."""
        self._hass = hass
        self._sensor_source_id = source_entity
        self._tariff_id = tariff_entity
        self._source_entity_id = False
        self._round_digits = round_digits
        self._state = 0
        self._last_reset = None
        self._tariffs = {}

        if name:
            self._name = name
        else:
            self._name = '{} meter'.format(source_entity)

        self._unit_of_measurement = "kWh"
        self._unit_of_measurement_scale = None

    async def async_reset(self):
        """Reset meter counters."""
        _LOGGER.debug("Reset energy meter %s", self.name)
        self._state = 0
        self._last_reset = dt_util.utcnow()
        for k in self._tariffs:
            self._tariffs[k] = 0

    async def async_added_to_hass(self):
        """Handle entity which will be added."""
        await super().async_added_to_hass()
        state = await self.async_get_last_state()
        if state:
            self._state = float(state.state)

        if self._tariff_id:
            self._current_tariff = self._hass.states.get(self._tariff_id).state
            if self._current_tariff not in self._tariffs:
                self._tariffs[self._current_tariff] = 0

        @callback
        def async_calc_energy(entity, old_state, new_state):
            """Handle the sensor state changes."""
            if old_state is None:
                return

            if self._unit_of_measurement_scale is None:
                unit_of_measurement = new_state.attributes.get(
                    ATTR_UNIT_OF_MEASUREMENT)
                if unit_of_measurement == UNIT_WATTS:
                    self._source_entity_id = True
                    self._unit_of_measurement_scale = 1000
                elif unit_of_measurement == UNIT_KILOWATTS:
                    self._source_entity_id = True
                    self._unit_of_measurement_scale = 1
                elif unit_of_measurement == UNIT_KILOWATTS_HOUR:
                    self._unit_of_measurement_scale = 0
                else:
                    _LOGGER.error("Unsupported power/energy unit: %s",
                                  unit_of_measurement)
                    return

            try:
                if self._source_entity_id:
                    # energy as the Riemann integral of previous measures.
                    elapsed_time = (new_state.last_updated
                                    - old_state.last_updated).total_seconds()
                    area = (float(new_state.state)
                            + float(old_state.state))*elapsed_time/2
                    kwh = area / (self._unit_of_measurement_scale * 3600)
                else:
                    kwh = float(new_state.state) - float(old_state.state)

                self._state += kwh
                if self._tariff_id:
                    self._tariffs[self._current_tariff] += kwh

            except ValueError:
                _LOGGER.warning("Unable to store state. "
                                "Only numerical states are supported")

            self._hass.async_add_job(self.async_update_ha_state, True)

        async_track_state_change(
            self._hass, self._sensor_source_id, async_calc_energy)

        @callback
        def async_change_tariff(entity, old_state, new_state):
            """Handle tariff transitions."""
            self._current_tariff = new_state.state
            if self._current_tariff not in self._tariffs:
                self._tariffs[self._current_tariff] = 0

        if self._tariff_id:
            async_track_state_change(
                self._hass, self._tariff_id, async_change_tariff)

    @property
    def name(self):
        """Return the name of the sensor."""
        return self._name

    @property
    def state(self):
        """Return the state of the sensor."""
        return round(self._state, self._round_digits)

    @property
    def unit_of_measurement(self):
        """Return the unit the value is expressed in."""
        return UNIT_OF_MEASUREMENT

    @property
    def should_poll(self):
        """No polling needed."""
        return False

    @property
    def device_state_attributes(self):
        """Return the state attributes of the sensor."""
        state_attr = {
            ATTR_SOURCE_ID: self._sensor_source_id,
            ATTR_LAST_RESET: self._last_reset,
        }
        for k, v in self._tariffs.items():
            state_attr[k] = round(v, self._round_digits)
        return state_attr

    @property
    def icon(self):
        """Return the icon to use in the frontend, if any."""
        return ICON
