"""
Component to track electricity tariff

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
    async_track_point_in_time, async_track_time_change)
from homeassistant.util import dt as dt_util

REQUIREMENTS = ['python-electricity==0.0.4']

_LOGGER =  logging.getLogger(__name__)

CONF_COUNTRY = 'country'
CONF_OPERATOR = 'operator'
CONF_PLAN = 'plan'
CONF_SOURCE_SENSOR = 'source'
CONF_DISABLE_METERS = 'disable_meters'

ATTR_TARIFFS = 'tariffs'

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
        self.country = config[CONF_COUNTRY]
        self.operator = config[CONF_OPERATOR]
        self.plan = config[CONF_PLAN]
        self._tariffs = [] 
        self._state = None

    async def async_added_to_hass(self):
        """Setup all required entities and automations."""
        from electricity.tariffs import Operators

        if self.country not in Operators:
            self.hass.components.persistent_notification.create(
                "<p><b>Error</b>: Country <em>{}</em> not supported.</p>"
                "Check logs for list of supported options".format(self.country),
                title="Electicity component",
                notification_id="electricity_error_country")
            _LOGGER.error("Country <%s> unsupported. Supported: %s",
                          self.country, ",".join(Operators))
            return
        if self.operator not in Operators[self.country]:
            self.hass.components.persistent_notification.create(
                "<p><b>Error</b>: Operator <em>{}</em> not supported.</p>"
                "Check logs for list of supported options".format(self.operator),
                title="Electicity component",
                notification_id="electricity_error_operator")
            _LOGGER.error("Operator <%s> unsupported. Supported: %s",
                          self.operator, ",".join(Operators[self.country]))
            return
        if self.plan not in Operators[self.country]\
                                     [self.operator].tariff_periods():
            self.hass.components.persistent_notification.create(
                "<p><b>Error</b>: Plan <em>{}</em> not supported.</p>"
                "Check logs for list of supported options".format(self.plan),
                title="Electicity component",
                notification_id="electricity_error_plan")
            _LOGGER.error("Plan <%s> unsupported. Supported: %s", self.plan, 
                          ",".join(Operators[self.country][self.operator].tariff_periods()))
            return


        self.my_plan = Operators[self.country][self.operator](plan=self.plan)
        
        self._state = self.my_plan.current_tariff(dt_util.now())
        self._tariffs = self.my_plan.tariffs()

        async_track_time_change(self.hass, self.timer_update, minute=range(0,60,15))

    @callback
    def timer_update(self, now):
        new_state = self.my_plan.current_tariff(now)
     
        if new_state != self._state:
            _LOGGER.debug("Changing from %s to %s", self._state, new_state)
            self._state = new_state
            self.schedule_update_ha_state()

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

    @property
    def device_state_attributes(self):
        """Return the state attributes."""
        if self._tariffs:
            return {
                ATTR_TARIFFS: self._tariffs,
            }
