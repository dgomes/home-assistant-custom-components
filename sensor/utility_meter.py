"""
Utility meter from sensors providing raw data.

For more details about this platform, please refer to the documentation at
https://home-assistant.io/components/sensor.utility_meter/
"""
import logging

import voluptuous as vol

import homeassistant.util.dt as dt_util
import homeassistant.helpers.config_validation as cv
from homeassistant.components.sensor import (DOMAIN, PLATFORM_SCHEMA)
from homeassistant.const import (
    CONF_NAME, ATTR_UNIT_OF_MEASUREMENT, ATTR_ENTITY_ID,
    EVENT_HOMEASSISTANT_START)
from homeassistant.core import callback
from homeassistant.helpers.event import async_track_state_change
from homeassistant.helpers.restore_state import RestoreEntity

_LOGGER = logging.getLogger(__name__)

ATTR_SOURCE_ID = 'source'
ATTR_STATUS = 'status'
ATTR_PERIOD = 'meter period'
ATTR_LAST_PERIOD = 'last period'
ATTR_LAST_RESET = 'last reset'

DATA_KEY = 'sensor.utility_meter'

SERVICE_START_PAUSE = 'utility_meter_start_pause'
SERVICE_RESET = 'utility_meter_reset'

HOURLY = 'hourly'
DAILY = 'daily'
WEEKLY = 'weekly'
MONTHLY = 'monthly'
YEARLY = 'yearly'

METER_TYPES = [HOURLY, DAILY, WEEKLY, MONTHLY, YEARLY]

SERVICE_METER_SCHEMA = vol.Schema({
    vol.Required(ATTR_ENTITY_ID): cv.entity_id,
})

CONF_SOURCE_SENSOR = 'source'
CONF_METER_TYPE = 'cycle'
CONF_METER_OFFSET = 'offset'

ICON = 'mdi:counter'

PRECISION = 3
PAUSED = "paused"
COLLECTING = "collecting"

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend({
    vol.Required(CONF_SOURCE_SENSOR): cv.entity_id,
    vol.Optional(CONF_NAME): cv.string,
    vol.Optional(CONF_METER_TYPE): vol.In(METER_TYPES),
    vol.Optional(CONF_METER_OFFSET, default=0): cv.positive_int,
})


async def async_setup_platform(hass, config, async_add_entities,
                               discovery_info=None):
    """Set up the utility meter sensor."""
    if DATA_KEY not in hass.data:
        hass.data[DATA_KEY] = {}

    def run_setup():
        """Delay the setup until Home Assistant is fully initialized.

        This allows any entities to be created already
        """

        meter = UtilityMeterSensor(hass,
                                   config[CONF_SOURCE_SENSOR],
                                   config.get(CONF_NAME),
                                   config.get(CONF_METER_TYPE),
                                   config.get(CONF_METER_OFFSET))

        async_add_entities([meter])

        hass.services.async_register(DOMAIN, SERVICE_START_PAUSE,
                                     async_start_pause_meter,
                                     schema=SERVICE_METER_SCHEMA)
        hass.services.async_register(DOMAIN, SERVICE_RESET,
                                     async_reset_meter,
                                     schema=SERVICE_METER_SCHEMA)

    @callback
    async def async_start_pause_meter(service):
        """Process service start_pause meter."""
        if service.data.get(ATTR_ENTITY_ID) in hass.data[DATA_KEY]:
            await hass.data[DATA_KEY]\
                [service.data.get(ATTR_ENTITY_ID)].async_start_pause_meter()

    @callback
    async def async_reset_meter(service):
        """Process service reset meter."""
        if service.data.get(ATTR_ENTITY_ID) in hass.data[DATA_KEY]:
            await hass.data[DATA_KEY]\
                [service.data.get(ATTR_ENTITY_ID)].async_reset_meter()

    # Wait until start event is sent to load this component.
    hass.bus.async_listen_once(EVENT_HOMEASSISTANT_START, run_setup)

class UtilityMeterSensor(RestoreEntity):
    """Representation of an energy sensor."""

    def __init__(self, hass, source_entity, name, meter_type, meter_offset=0):
        """Initialize the min/max sensor."""
        self._hass = hass
        self._sensor_source_id = source_entity
        self._state = 0
        self._last_period = 0
        self._last_reset = dt_util.now()
        self._collecting = None
        if name:
            self._name = name
        else:
            self._name = '{} meter'.format(source_entity)
        self._unit_of_measurement = None
        self._period = meter_type
        self._period_offset = meter_offset

        if meter_type == HOURLY:
            async_track_utc_time_change(hass, async_reset_meter, minute=meter_offset)
        if meter_type == DAILY:
            async_track_utc_time_change(hass, async_reset_meter, hour=meter_offset)
        elif meter_type == [WEEKLY, MONTHLY, YEARLY]:
            async_track_utc_time_change(hass, lambda: async_reset_meter(False), hour=0)

    @callback
    def async_reading(self, entity, old_state, new_state):
        """Handle the sensor state changes."""
        if old_state is None:
            return

        if self._unit_of_measurement is None:
            self._unit_of_measurement = new_state.attributes.get(
                ATTR_UNIT_OF_MEASUREMENT)

        try:
            diff = float(new_state.state) - float(old_state.state)
            self._state += diff

        except ValueError:
            _LOGGER.warning("Unable to store %s state. "
                            "Only numerical states are supported", entity)

        self._hass.async_add_job(self.async_update_ha_state, True)

    async def async_start_pause_meter(self):
        """Start/Pause meter."""
        if self._collecting is None:
            self._collecting = async_track_state_change(
                self._hass, self._sensor_source_id, self.async_reading)
        else:
            self._collecting()
            self._collecting = None
        _LOGGER.debug("%s energy meter %s",
                      COLLECTING if self._collecting is not None
                      else PAUSED, self.name)
        self._hass.async_add_job(self.async_update_ha_state, True)

    async def async_reset_meter(self, force=True):
        """Reset meter."""
        now = dt_util.now()
        if not force:
            if self._period == WEEKLY and now.weekday() != self._period_offset:
                return
            if self._period == MONTHLY and now.day() != (1 + self._period_offset):
                return
            if self._period == YEARLY and now.month() != (1 + self._period_offset):
                return

        _LOGGER.debug("Reset energy meter %s", self.name)
        self._last_reset = now
        self._last_period = self._state
        self._state = 0
        self._hass.async_add_job(self.async_update_ha_state, True)

    async def async_added_to_hass(self):
        """Handle entity which will be added."""
        state = await self.async_get_last_state()
        if state:
            self._state = float(state.state)
            self._unit_of_measurement = state.unit_of_measurement
            self._last_period = state.state_attr[ATTR_LAST_PERIOD]
            self._last_reset = state.state_attr[ATTR_LAST_RESET]
        await self.async_start_pause_meter()

        self._hass.data[DATA_KEY][self.entity_id] = self

    @property
    def name(self):
        """Return the name of the sensor."""
        return self._name

    @property
    def state(self):
        """Return the state of the sensor."""
        return self._state

    @property
    def unit_of_measurement(self):
        """Return the unit the value is expressed in."""
        return self._unit_of_measurement

    @property
    def should_poll(self):
        """No polling needed."""
        return False

    @property
    def device_state_attributes(self):
        """Return the state attributes of the sensor."""
        state_attr = {
            ATTR_SOURCE_ID: self._sensor_source_id,
            ATTR_STATUS: PAUSED if self._collecting is None else COLLECTING,
            ATTR_LAST_PERIOD: self._last_period,
            ATTR_LAST_RESET: self._last_reset,
        }
        if self._period is not None:
            state_attr[ATTR_PERIOD] = self._period
        return state_attr

    @property
    def icon(self):
        """Return the icon to use in the frontend, if any."""
        return ICON