import logging

from homeassistant.core import callback
from homeassistant.helpers.restore_state import RestoreEntity
from ..energy_meter import (DATA_ENERGY_METER, UNIT_KILOWATTS_HOUR, ATTR_TARIFF, UPDATE_TOPIC, DOMAIN)

DEPENDENCIES = ['energy_meter']

_LOGGER = logging.getLogger(__name__)

ICON = 'mdi:counter'

async def async_setup_platform(hass, config, async_add_entities, discovery_info=None):
    """Setup the sensor platform."""

    meterdata = hass.data[DATA_ENERGY_METER]
    
    tariff = discovery_info[ATTR_TARIFF] 

    meter = EnergyMeterSensor(meterdata, tariff)

    async_add_entities([meter])

class EnergyMeterSensor(RestoreEntity):
    """Representation of a Sensor."""

    def __init__(self, meterdata, tariff):
        """Initialize the sensor."""
        self._state = None
        self._meterdata = meterdata
        self._tariff = tariff
        self._name = "{}_{}".format(DOMAIN, tariff)

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
        """Return the unit of measurement."""
        return UNIT_KILOWATTS_HOUR 

    @property
    def should_poll(self):
        """No polling needed."""
        return False

    @property
    def icon(self):
        """Return the icon to use in the frontend, if any."""
        return ICON

    async def async_added_to_hass(self):
        """Handle entity which will be added."""
        await super().async_added_to_hass()
        state = await self.async_get_last_state()
        if state:
            self._meterdata.data[self._tariff] += float(state.state)
            self._state = self._meterdata.data[self._tariff]

        """Register callbacks."""
        self.hass.helpers.dispatcher.async_dispatcher_connect(
            UPDATE_TOPIC, self.async_update_callback)

    @callback
    def async_update_callback(self):
        """Update state."""
        if self._tariff in self._meterdata.data:
            self._state = self._meterdata.data[self._tariff] 
            self.async_schedule_update_ha_state()

