"""
Home MQTT (https://github.com/dgomes/home_mqtt) platform for the cover component.

For more details about this platform, please refer to the documentation
https://github.com/dgomes/home_mqtt
"""
import logging

import voluptuous as vol

from homeassistant.util import dt as dt_util
from homeassistant.core import callback
from homeassistant.components.cover import (
    CoverDevice, PLATFORM_SCHEMA,
    ATTR_POSITION)
from homeassistant.const import (STATE_OPEN, STATE_CLOSED,
    CONF_COVERS, CONF_DELAY_TIME, CONF_FRIENDLY_NAME)
from homeassistant.helpers.event import track_utc_time_change
from homeassistant.components import mqtt
from homeassistant.helpers.restore_state import RestoreEntity 
import homeassistant.helpers.config_validation as cv

DEPENDENCIE = ['mqtt']

_LOGGER = logging.getLogger(__name__)

CONF_RELAY_UP = "relay_up"
CONF_RELAY_DOWN = "relay_down"

M_DUINO_RELAY = "devices/m-duino/relay/{}"
M_DUINO_RELAY_SET = M_DUINO_RELAY + "/set"

COVER_SCHEMA = vol.Schema({
    vol.Required(CONF_RELAY_UP): cv.positive_int,
    vol.Required(CONF_RELAY_DOWN): cv.positive_int,
    vol.Optional(CONF_DELAY_TIME, default=30000): cv.positive_int,
})

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend({
    vol.Required(CONF_COVERS): vol.Schema({cv.slug: COVER_SCHEMA}),
})


async def async_setup_platform(hass, config, async_add_entities, discovery_info=None):
    """Set up the covers."""
    covers = []
    for cover_name, cover_config in config.get(CONF_COVERS, {}).items():
        covers.append(
            HomeMQTTCover(
                hass,
                cover_name,
                cover_config[CONF_RELAY_UP],
                cover_config[CONF_RELAY_DOWN],
                cover_config[CONF_DELAY_TIME]
            )
        )

    if not covers:
        _LOGGER.error("No covers added")
        return

    async_add_entities(covers)


class HomeMQTTCover(CoverDevice, RestoreEntity):
    """Representation of a demo cover."""

    def __init__(self, hass, name, relay_up, relay_down, delay_time):
        """Initialize the cover."""
        self.hass = hass
        self._name = name
        self._relay_up = relay_up
        self._relay_down = relay_down
        self._delay_time = delay_time
        self._is_closing = self._is_opening = False
    
        self._closed = False
        self._position = 50
        self._timer = None

    async def async_added_to_hass(self):
        """Call when entity about to be added to hass."""
        state = await self.async_get_last_state()
        if state:
            _LOGGER.debug("last state of %s = %s", self._name, state)
            self._position = state.attributes.get('current_position', 50)
            
        @callback
        def update_status(topic, payload, qos):
            if self._timer is not None:
                elapsed_time = dt_util.utcnow() - self._timer
                elapsed_miliseconds = int(elapsed_time.seconds * 1000 + elapsed_time.microseconds / 1000)
                _LOGGER.debug("elapsed_miliseconds for %s = %s ", self._name, elapsed_miliseconds)
                self._timer = None
            else:
                elapsed_miliseconds = 0
            
            if topic == M_DUINO_RELAY.format(self._relay_up):
                if payload == "true":
                    _LOGGER.debug("Opening %s", self._name)
                    self._is_opening = True
                    self._timer = dt_util.utcnow()
                else:
                    self._is_opening = False
                    self._position+= int( (elapsed_miliseconds/self._delay_time) * 100 )
            elif topic == M_DUINO_RELAY.format(self._relay_down):
                if payload == "true":
                    _LOGGER.debug("Closing %s", self._name)
                    self._is_closing = True
                    self._timer = dt_util.utcnow()
                else:
                    self._is_closing = False
                    self._position-= int( (elapsed_miliseconds/self._delay_time) * 100 )
           
            self._closed = False
            if self._position >= 99: #this accounts for timing errors
                self._position = 100
            elif self._position <= 1:
                self._position = 0
                self._closed = True

            self.async_schedule_update_ha_state(True)

        await self.hass.components.mqtt.async_subscribe(M_DUINO_RELAY.format(self._relay_up), update_status)
        await self.hass.components.mqtt.async_subscribe(M_DUINO_RELAY.format(self._relay_down), update_status)

    @property
    def name(self):
        """Return the name of the cover."""
        return self._name

    @property
    def current_cover_position(self):
        """Return current position of cover."""
        return self._position

    async def async_set_cover_position(self, **kwargs):
        """Move the cover to a specific position."""
        position = kwargs.get(ATTR_POSITION)
        _LOGGER.debug("set position %s = %s", self._name, position)

        diff = self._position - position
        if diff > 0:
            _LOGGER.debug("Close")
            self._operate_cover(self._relay_down, diff * self._delay_time / 100)
            self._is_closing = True
        elif diff < 0:
            _LOGGER.debug("Open")
            self._operate_cover(self._relay_up, abs(diff) * self._delay_time / 100)
            self._is_opening = True

    @property
    def should_poll(self):
        """Can't poll anything."""
        return False

    @property
    def is_closed(self):
        """Return if the cover is closed."""
        return self._closed

    @property
    def is_closing(self):
        """Return if the cover is closing."""
        return self._is_closing

    @property
    def is_opening(self):
        """Return if the cover is opening."""
        return self._is_opening

    @property
    def device_class(self):
        """Return the class of this device, from component DEVICE_CLASSES."""
        return "window" 

    @property
    def unique_id(self):
        """Return a unique, HASS-friendly identifier for this entity."""
        return "m-duino-{}-{}-{}".format(self._name, self._relay_up, self._relay_down)

    def _operate_cover(self, relay, time):
        time = int(time)
        if self._is_closing or self._is_opening:
            _LOGGER.error("Can't operate cover %s", self._name)
            return

        _LOGGER.debug("_operate_cover %s @ %s for %s msec ", self._name, relay, time)

        self.hass.components.mqtt.async_publish(
            M_DUINO_RELAY_SET.format(relay), time, qos=0, retain=False)

    async def async_close_cover(self, **kwargs):
        """Close the cover."""
        _LOGGER.debug("async_close_cover (%s)", self._relay_down)
        await self.async_set_cover_position(position=0)
        self._is_closing = True 

    async def async_open_cover(self, **kwargs):
        """Open the cover."""
        _LOGGER.debug("async_open_cover (%s)", self._relay_up)
        await self.async_set_cover_position(position=100)
        self._is_opening = True 
        
    async def async_stop_cover(self, **kwargs):
        """Stop the cover."""
        relays = []
        if self._is_opening:
            relays = [self._relay_up, self._relay_down]
        elif self._is_closing:
            relays = [self._relay_down, self._relay_up]
        else:
            self._position = 50 
            self.async_schedule_update_ha_state(True)
        
        for r in relays:
            self.hass.components.mqtt.async_publish(
                M_DUINO_RELAY_SET.format(r), "false", qos=0, retain=False)
