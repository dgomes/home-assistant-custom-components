"""
Component to track utility consumption over given periods of time.

For more details about this component, please refer to the documentation
at https://www.home-assistant.io/components/utility_meter/
"""

import logging

import voluptuous as vol

from homeassistant.core import callback
from homeassistant.const import (ATTR_ENTITY_ID, CONF_NAME)
from homeassistant.util import slugify
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers import discovery
from homeassistant.helpers.dispatcher import dispatcher_send
from homeassistant.helpers.entity_component import EntityComponent
from homeassistant.helpers.restore_state import RestoreEntity
from .const import (
    DOMAIN, SIGNAL_START_PAUSE_METER, SIGNAL_RESET_METER,
    METER_TYPES, CONF_SOURCE_SENSOR, CONF_METER_TYPE, CONF_METER_OFFSET,
    CONF_TARIFF_ENTITY, CONF_TARIFF, CONF_TARIFFS, CONF_PAUSED, CONF_METER,
    DATA_UTILITY, UTILITY_COMPONENT)

_LOGGER = logging.getLogger(__name__)

TARIFF_ICON = "mdi:cash-multiple"

ATTR_OPTIONS = 'tariffs'

SERVICE_START_PAUSE = 'start_pause'
SERVICE_RESET = 'reset'
SERVICE_SELECT_TARIFF = 'select_tariff'
SERVICE_SELECT_NEXT_TARIFF = 'next_tariff'

SERVICE_METER_SCHEMA = vol.Schema({
    vol.Required(ATTR_ENTITY_ID): cv.entity_ids,
})

SERVICE_SELECT_TARIFF_SCHEMA = SERVICE_METER_SCHEMA.extend({
    vol.Required(CONF_TARIFF): cv.string
})

METER_CONFIG_SCHEMA = vol.Schema({
    vol.Required(CONF_SOURCE_SENSOR): cv.entity_id,
    vol.Optional(CONF_NAME): cv.string,
    vol.Optional(CONF_METER_TYPE): vol.In(METER_TYPES),
    vol.Optional(CONF_METER_OFFSET, default=0): cv.positive_int,
    vol.Optional(CONF_TARIFFS, default=[]): vol.All(
        cv.ensure_list, [cv.string]),
})

CONFIG_SCHEMA = vol.Schema({
    DOMAIN: vol.Schema({
        cv.slug: METER_CONFIG_SCHEMA,
    }),
}, extra=vol.ALLOW_EXTRA)

async def async_setup(hass, config):
    """Set up an Utility Meter."""
    component = EntityComponent(_LOGGER, DOMAIN, hass)
    hass.data[DATA_UTILITY] = {UTILITY_COMPONENT: component}

    for meter, conf in config.get(DOMAIN).items():
        _LOGGER.debug("Setup %s.%s", DOMAIN, meter)

        hass.data[DATA_UTILITY][meter] = conf

        if conf[CONF_TARIFFS] == []:
            #TODO melhor nome para este sensor
            hass.async_create_task(discovery.async_load_platform(
                hass, "sensor", "utility_meter", 
                {CONF_METER: meter}, config))
        else:
            # create tariff selection
            await component.async_add_entities([
                TariffSelect(meter, list(conf[CONF_TARIFFS]))
            ])
            hass.data[DATA_UTILITY][meter][CONF_TARIFF_ENTITY] =\
                "{}.{}".format(DOMAIN, meter)

            for tariff in conf[CONF_TARIFFS]:
                tariff_conf = {
                    CONF_METER: meter,
                    CONF_NAME: "{} {}".format(meter, tariff),
                    CONF_TARIFF: tariff,
                    }
                hass.async_create_task(discovery.async_load_platform(
                    hass, "sensor", "utility_meter", tariff_conf, config))

    @callback
    def async_service_reset_meter(service):
        """Process service to reset meter."""
        for entity in service.data[ATTR_ENTITY_ID]:
            dispatcher_send(hass, SIGNAL_RESET_METER, entity)

    hass.services.async_register(DOMAIN, SERVICE_RESET,
                                 async_service_reset_meter,
                                 schema=SERVICE_METER_SCHEMA)

    component.async_register_entity_service(
        SERVICE_SELECT_TARIFF, SERVICE_SELECT_TARIFF_SCHEMA,
        'async_select_tariff'
    )

    component.async_register_entity_service(
        SERVICE_SELECT_NEXT_TARIFF, SERVICE_METER_SCHEMA,
        'async_next_tariff'
    )

    return True

class TariffSelect(RestoreEntity):
    """Representation of a Tariff selector."""

    def __init__(self, name, options):
        """Initialize a tariff selector."""
        self._name = name
        self._current_tariff = None 
        self._tariffs = options
        self._icon = TARIFF_ICON 

    async def async_added_to_hass(self):
        """Run when entity about to be added."""
        await super().async_added_to_hass()
        if self._current_tariff is not None:
            return

        state = await self.async_get_last_state()
        if not state or state.state not in self._tariffs:
            self._current_tariff = self._tariffs[0]
        else:
            self._current_tariff = state.state

    @property
    def should_poll(self):
        """If entity should be polled."""
        return False

    @property
    def name(self):
        """Return the name of the select input."""
        return self._name

    @property
    def icon(self):
        """Return the icon to be used for this entity."""
        return self._icon

    @property
    def state(self):
        """Return the state of the component."""
        return self._current_tariff

    @property
    def state_attributes(self):
        """Return the state attributes."""
        return {
            ATTR_OPTIONS: self._tariffs,
        }

    async def async_select_tariff(self, tariff):
        """Select new option."""
        if tariff not in self._tariffs:
            _LOGGER.warning('Invalid tariff: %s (possible tariffs: %s)',
                            option, ', '.join(self._tariffs))
            return
        self._current_tariff = tariff 
        await self.async_update_ha_state()

    async def async_next_tariff(self):
        """Offset current index."""
        current_index = self._tariffs.index(self._current_tariff)
        new_index = (current_index + 1) % len(self._tariffs)
        self._current_tariff = self._tariffs[new_index]
        await self.async_update_ha_state()

