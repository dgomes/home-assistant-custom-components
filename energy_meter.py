"""
This component provides support for multiple tariffs energy meters 

For more details about this component, please refer to the documentation at
https://home-assistant.io/components/energy_meter/
"""
import logging

import voluptuous as vol

import homeassistant.util.dt as dt_util
import homeassistant.helpers.config_validation as cv
from homeassistant.components.sensor import (DOMAIN, PLATFORM_SCHEMA)
from homeassistant.const import (
    CONF_NAME, ATTR_UNIT_OF_MEASUREMENT, ATTR_ENTITY_ID)
from homeassistant.helpers import discovery
from homeassistant.core import callback
from homeassistant.helpers.event import async_track_state_change
from homeassistant.helpers.restore_state import RestoreEntity

_LOGGER = logging.getLogger(__name__)

DATA_ENERGY_METER = 'energy_meter'
DOMAIN = 'energy_meter'
UPDATE_TOPIC = DOMAIN + "_update"

SERVICE_RESET = 'reset'

SERVICE_RESET_SCHEMA = vol.Schema({
    vol.Required(ATTR_ENTITY_ID): cv.entity_id,
})

CONF_SOURCE_SENSOR = 'source'
CONF_TARIFF = 'tariff'

ATTR_TARIFF = 'tariff'

UNIT_KILOWATTS_HOUR = "kWh"

CONFIG_SCHEMA = vol.Schema({
    DOMAIN: vol.Schema({
        vol.Optional(CONF_NAME): cv.string,
        vol.Required(CONF_SOURCE_SENSOR): cv.entity_id,
        vol.Required(CONF_TARIFF): cv.entity_id,
    })
}, extra=vol.ALLOW_EXTRA)

async def async_setup(hass, config):
    """Set up an Energy Meter component."""
    conf = config[DOMAIN]

    hass.data[DATA_ENERGY_METER] = MeterData(conf)

    async def async_reset_meter(service):
        if service.data.get(ATTR_ENTITY_ID) in hass.data[DATA_ENERGY_METER].sensors:
            await hass.data[DATA_ENERGY_METER].sensors[service.data.get(ATTR_ENTITY_ID)].async_reset()

    # register service
    hass.services.async_register(DOMAIN, SERVICE_RESET,
                                 async_reset_meter,
                                 schema=SERVICE_RESET_SCHEMA)
   
    @callback
    def update_meters(entity, old_state, new_state):
        """Handle the sensor state changes."""
        if old_state is None:
            return

        unit_of_measurement = new_state.attributes.get(ATTR_UNIT_OF_MEASUREMENT)
        if unit_of_measurement != UNIT_KILOWATTS_HOUR:
            _LOGGER.error("Unsupported power/energy unit: %s",
                          unit_of_measurement)
            return

        current_tariff = hass.data[DATA_ENERGY_METER].current_tariff
        if current_tariff is None:
            current_tariff = hass.states.get(self.conf[CONF_TARIFF]).state
            hass.data[DATA_ENERGY_METER].add_sensor(current_tariff)

        try:
            kwh = float(new_state.state) - float(old_state.state)
            hass.data[DATA_ENERGY_METER].data[current_tariff] += kwh
            hass.helpers.dispatcher.dispatcher_send(UPDATE_TOPIC)

        except ValueError:
            _LOGGER.warning("Unable to process energy readings. "
                            "Only numerical states are supported")

    async_track_state_change(hass, conf[CONF_SOURCE_SENSOR], update_meters)
    
    @callback
    def change_tariff(entity, old_state, new_state):
        """Handle tariff transitions."""
        if new_state.state not in hass.data[DATA_ENERGY_METER].data:
            hass.data[DATA_ENERGY_METER].add_sensor(new_state.state)

            hass.async_create_task(discovery.async_load_platform(hass, 'sensor', DOMAIN, {'tariff': new_state.state}, conf))

    async_track_state_change(hass, conf[CONF_TARIFF], change_tariff)

    return True


class MeterData:
    """An object to store the Energy Meter data."""

    def __init__(self, conf):
        """Initialize Energy Meter data store."""
        self.conf = conf
        self.sensors = {}
        self.data = {}
        self.current_tariff = None

    def add_sensor(self, tariff_id):
        """Add a sensor that tracks a given tariff."""
        self.sensors[tariff_id] = None 
        self.data[tariff_id] = 0
        
        self.current_tariff = tariff_id
