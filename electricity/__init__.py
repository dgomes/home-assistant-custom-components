"""
Component to track electricity consumption.

For more details about this component, please refer to the documentation
at http://github.com/dgomes/home-assistant-custom-components/electricity/
"""
import logging

import voluptuous as vol
from datetime import date

from homeassistant.core import callback
from homeassistant.const import ATTR_ENTITY_ID
from homeassistant.helpers import discovery
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.entity import Entity
from homeassistant.helpers.entity_component import EntityComponent
from homeassistant.helpers.event import (
    async_track_point_in_utc_time, async_track_utc_time_change)
from homeassistant.util import dt as dt_util

REQUIREMENTS = ['python-electricity==0.0.3']

_LOGGER =  logging.getLogger(__name__)

CONF_COUNTRY = 'country'
CONF_OPERATOR = 'operator'
CONF_PLAN = 'plan'
CONF_SOURCE_SENSOR = 'source'
CONF_DISABLE_METERS = 'disable_meters'

DOMAIN = 'electricity'

ICON = "mdi:transmission-tower"

UTILITY_METER_NAME_FORMAT = "{} {}"

def _cv_supported_operator(cfg):
    from electricity.tariffs import Operators
    import electricity.tariffs as tariffs

    country = cfg.get(CONF_COUNTRY)
    if country not in Operators:
        raise vol.Invalid("Country {} is not supported."
                          "Refer to "
                          "https://github.com/dgomes/python-electricity".format(
                          country))
    
    operator = cfg.get(CONF_OPERATOR)
    if operator not in Operators[country]:
        raise vol.Invalid("Operator {} is not supported."
                          "Refer to "
                          "https://github.com/dgomes/python-electricity".format(
                          operator))
 
    plan = cfg.get(CONF_PLAN)
    if plan not in Operators[country][operator].tariff_periods():
        raise vol.Invalid("Plan {} is not supported."
                          "Refer to "
                          "https://github.com/dgomes/python-electricity".format(
                          plan))
        
    return cfg

CONFIG_SCHEMA = vol.Schema({
    DOMAIN: vol.Schema({
        cv.slug: vol.All({
            vol.Required(CONF_COUNTRY): cv.string,
            vol.Required(CONF_OPERATOR): cv.string,
            vol.Required(CONF_PLAN): cv.string,
            vol.Required(CONF_SOURCE_SENSOR): cv.entity_id,
            vol.Optional(CONF_DISABLE_METERS, default=False): cv.boolean,
        }) #, _cv_supported_operator)
    })
}, extra=vol.ALLOW_EXTRA)

async def async_setup(hass, config):
    """Set up an electricity monitor."""
    component = EntityComponent(_LOGGER, DOMAIN, hass)

    entities = []

    for name, cfg in config[DOMAIN].items():
        _LOGGER.debug(name, cfg)
        entities.append(EletricityEntity(name, cfg))

    await component.async_add_entities(entities)
    return True


class EletricityEntity(Entity):
    """Representation of an Electricity Contract."""

    def __init__(self, name, config):
        """Initialize an Electricity Contract."""
        self._name = name
        self.config = config
        self.country = config[CONF_COUNTRY]
        self.operator = config[CONF_OPERATOR]
        self.plan = config[CONF_PLAN]
        self.source_sensor = config[CONF_SOURCE_SENSOR]
        if config[CONF_DISABLE_METERS]:
            self.utility_meters = None
        else:
            self.utility_meters = []

    async def async_added_to_hass(self):
        """Setup all required entities and automations."""
        from electricity.tariffs import (Operators, WEEKLY, MONTHLY, YEARLY)

        self.my_plan = Operators[self.country][self.operator](plan=self.plan)
        if self.my_plan.billing_period() == WEEKLY:
            meter_type = "weekly"
        elif self.my_plan.billing_period() == MONTHLY:
            meter_type = "monthly"
        elif self.my_plan.billing_period() == YEARLY:
            meter_type = "yearly"
        self._state = self.my_plan.current_tariff(dt_util.now())

        if self.utility_meters is not None:
            for tariff in self.my_plan.tariffs():
                _LOGGER.debug("Create utility_meter %s", tariff)
                config = {
                          'name': UTILITY_METER_NAME_FORMAT.format(self.name, tariff),
                          'source': self.source_sensor,
                          'meter_type': meter_type,
                          'paused': self._state != tariff,
                         }
                _LOGGER.debug(config)
                self.hass.async_create_task(discovery.async_load_platform(self.hass, "sensor", "utility_meter", config, self.config))
                
        async_track_utc_time_change(self.hass, self.timer_update, second=range(0,60,15))

    @callback
    def timer_update(self, now):
        new_state = self.my_plan.current_tariff(now)
     
        if self.utility_meters is not None and (
                self.utility_meters == [] or 
                len(self.utility_meters) != len(self.my_plan.tariffs())
                ):
            states = self.hass.states.async_all()
            self.utility_meters = [s.entity_id for s in states for t in self.my_plan.tariffs() if s.name == UTILITY_METER_NAME_FORMAT.format(self.name, t)]

        if new_state != self._state:
            _LOGGER.debug("Changing from %s to %s", self._state, new_state)
            self._state = new_state
            self.schedule_update_ha_state()

            if self.utility_meters is not None:
                service_data = {ATTR_ENTITY_ID: self.utility_meters}
                self.hass.async_create_task(self.hass.services.async_call("sensor", "utility_meter_start_pause", service_data))

    @property
    def should_poll(self):
        """If entity should be polled."""
        return False

    @property
    def name(self):
        """Return the name of the Electricity contract."""
        return self._name

    @property
    def state(self):
        """Return the state as the current tariff."""
        return self._state

    @property
    def icon(self):
        """Return the icon to use in the frontend, if any."""
        return ICON
