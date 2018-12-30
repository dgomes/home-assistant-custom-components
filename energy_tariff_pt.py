"""
Support for tracking portuguese energy tariff periods 

For more details about this component, please refer to the documentation at
https://home-assistant.io/components/energy_
"""
import logging
from datetime import timedelta

import voluptuous as vol

from homeassistant.core import callback
from homeassistant.helpers.entity import Entity
from homeassistant.helpers.event import (
    async_track_point_in_utc_time, async_track_utc_time_change)
from homeassistant.const import (
    CONF_NAME, STATE_UNKNOWN)
from homeassistant.util import dt as dt_util
from homeassistant.helpers.entity_component import EntityComponent
import homeassistant.helpers.config_validation as cv

_LOGGER = logging.getLogger(__name__)

DOMAIN = 'energy_tariff_pt'

STATE_PONTA = 'Ponta'
STATE_CHEIAS = 'Cheias'
STATE_VAZIO_NORMAL = 'Vazio normal'
STATE_SUPER_VAZIO = 'Super vazio'

ATTR_TARIFF_PERIOD = 'Periodo Horário'

CONF_TARIFF_PERIOD = 'tariff_period'

DEFAULT_NAME = 'Energy Tariff'

CONF_BI_HORARIO_DIARIO = 'bi-horario-diario'
CONF_BI_HORARIO_SEMANAL = 'bi-horario-semanal'
CONF_TRI_HORARIO = 'tri-horario'

CONFIG_SCHEMA = vol.Schema({
    DOMAIN: vol.Schema({
        vol.Optional(CONF_NAME, default=DEFAULT_NAME): cv.string,
        vol.Required(CONF_TARIFF_PERIOD): vol.Any(CONF_BI_HORARIO_DIARIO,
                                                  CONF_BI_HORARIO_SEMANAL, 
                                                  CONF_TRI_HORARIO) 
        })
}, extra=vol.ALLOW_EXTRA)

async def async_setup(hass, config):
    """Track current energy tariff."""
    component = EntityComponent(_LOGGER, DOMAIN, hass)
    conf = config[DOMAIN]

    energy_tariff = EnergyTariff(hass, conf[CONF_NAME], conf[CONF_TARIFF_PERIOD]) 
   
    # update every 15min
    async_track_utc_time_change(hass, energy_tariff.timer_update, minute=range(0,60,15))
    await component.async_add_entities([energy_tariff])
    return True


class EnergyTariff(Entity):
    """Representation of the current EnergyTariff."""

    def __init__(self, hass, name, tariff):
        """Initialize the sun."""
        self.hass = hass
        self._name = name
        self._tariff = tariff

    async def async_added_to_hass(self):
        """Calculate the current tariff on start."""
        self.timer_update(dt_util.now())

    @property
    def name(self):
        """Return the name."""
        return self._name 

    @property
    def state(self):
        """Return the state of the sun."""
        return STATE_VAZIO_NORMAL

    @property
    def device_state_attributes(self):
        """Return the state attributes of the sensor."""
        state_attr = {
            ATTR_TARIFF_PERIOD: self._tariff
        }
        return state_attr

    def bi_horario_diario(self, time):
        if 0 <= time.hour < 8:
            return STATE_VAZIO_NORMAL
        elif 22 <= time.hour < 24:
            return STATE_VAZIO_NORMAL
        return STATE_CHEIAS

    def bi_horario_semanal(self, time):
        if 0 <= time.weekday() < 5:
            if 0 <= time.hour < 8:
                return STATE_VAZIO_NORMAL
        if time.weekday() == 5: 
            # Hora legal de Verão começa no 1º Domingo de Março e acaba no ultimo de Outubro
            # https://docs.python.org/3.3/library/datetime.html
            d = datetime(dt.year, 4, 1)  
            i_verao = d - timedelta(days=d.weekday() + 1)
            d = datetime(dt.year, 11, 1)
            f_verao = d - timedelta(days=d.weekday() + 1)
            if i_verao <= time.replace(tzinfo=None) < f_verao:
                if 0 <= time.hour < 9:
                    return STATE_VAZIO_NORMAL
                elif 14 <= time.hour < 20:      
                    return STATE_VAZIO_NORMAL
                elif 22 <= time.hour < 24:      
                    return STATE_VAZIO_NORMAL
            else:
                if datetime.time(0,00) <= time.time() < datetime.time(9,30):
                    return STATE_VAZIO_NORMAL
                elif datetime.time(13,00) <= time.time() < datetime.time(18,30):
                    return STATE_VAZIO_NORMAL
                elif 22 <= time.hour < 24:      
                    return STATE_VAZIO_NORMAL
        if time.weekday() == 6:
            return STATE_VAZIO_NORMAL
        return STATE_CHEIAS

    def tri_horario(self, time):
        return STATE_UNKNOWN 

    @callback
    def timer_update(self, time):
        """Needed to update solar elevation and azimuth."""
        if self._tariff == CONF_BI_HORARIO_DIARIO:
            self._state = self.bi_horario_diario(time)
        elif self._tariff == CONF_BI_HORARIO_SEMANAL:
            self._state = self.bi_horario_semanal(time)
        elif self._tariff == CONF_TRI_HORARIO:
            self._state = self.tri_horario(time)

        self.async_schedule_update_ha_state()
