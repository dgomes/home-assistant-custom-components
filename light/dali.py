"""
Support for DALI lights.

For more details about this platform, please refer to the documentation at
https://home-assistant.io/components/light.dali/
"""
import usb
import logging
from subprocess import check_output, CalledProcessError, STDOUT

import voluptuous as vol

from homeassistant.const import (CONF_NAME, CONF_ID, CONF_DEVICES)
from homeassistant.components.light import (
    ATTR_BRIGHTNESS, SUPPORT_BRIGHTNESS, Light, PLATFORM_SCHEMA)
import homeassistant.helpers.config_validation as cv

_LOGGER = logging.getLogger(__name__)

SUPPORT_DALI = SUPPORT_BRIGHTNESS

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend({
    vol.Required(CONF_DEVICES): vol.All(cv.ensure_list, [
        {
            vol.Required(CONF_ID): cv.string,
            vol.Required(CONF_NAME): cv.string,
        }
    ]),
})

def setup_platform(hass, config, add_devices, discovery_info=None):
    """Set up the DALI Light platform."""

    from threading import RLock
    from dali.driver.hasseb import HassebUsb

    driver = HassebUsb()
    driver_lock = RLock()

    add_devices(DALILight(driver, driver_lock, ballast) for ballast in config[CONF_DEVICES])

def to_dali_level(level):
    """Convert the given HASS light level (0-255) to DALI (0-254)."""
    return int((level * 254) / 255)


def to_hass_level(level):
    """Convert the given DALI (0-254) light level to HASS (0-255)."""
    return int((level * 255) / 254)

class DALILight(Light):
    """Representation of an DALI Light."""

    def __init__(self, driver, driver_lock, ballast):
        from dali.address import Short
        from dali.gear.general import QueryStatus 
        from dali.gear.general import QueryStatusResponse 
        from dali.gear.general import DTR0 
        from dali.gear.general import QueryPowerOnLevel
        from dali.gear.general import QueryLampPowerOn
        """Initialize a DALI Light."""
        self._id = ballast['id']
        self._name = ballast['name']
        self._brightness = 0
        self._state = False       
 
        self.driver = driver
        self.driver_lock = driver_lock
        self.addr = Short(int(self._id))


        with self.driver_lock:
            cmd = QueryPowerOnLevel(self.addr)
            r = self.driver.send(cmd)
            if r.value != None:
                self._brightness = to_hass_level(r.value.as_integer)

        with self.driver_lock:
            cmd = QueryLampPowerOn(self.addr)
            r = self.driver.send(cmd)
            if r.value != None:
                self._state = r.value 

    @property
    def name(self):
        """Return the display name of this light."""
        return self._name

    @property
    def brightness(self):
        """Return the brightness of the light."""

        return self._brightness

    @property
    def is_on(self):
        """Return true if light is on."""
        return self._state

    @property
    def supported_features(self):
        """Flag supported features."""
        return SUPPORT_DALI

    def turn_on(self, **kwargs):
        """Instruct the light to turn on."""
        from dali.gear.general import DAPC
 
        with self.driver_lock:
            self._brightness = kwargs.get(ATTR_BRIGHTNESS, 255)
            cmd = DAPC(self.addr, to_dali_level(self._brightness))
            r = self.driver.send(cmd)
            self._state = True

    def turn_off(self, **kwargs):
        """Instruct the light to turn off."""
        from dali.gear.general import Off 

        with self.driver_lock:
            cmd = Off(self.addr)
            r = self.driver.send(cmd)
            self._state = False 

    def update(self):
        """Fetch update state."""
        from dali.gear.general import QueryActualLevel
        from dali.gear.general import QueryLampPowerOn
        
        try:
            with self.driver_lock:
                cmd = QueryLampPowerOn(self.addr)
                r = self.driver.send(cmd)
                self._state = bool(r.value)
                _LOGGER.debug("{} is_on ? {}".format(self._id, self._state))
        except usb.core.USBError as e:
            _LOGGER.warning(e)
 
        if not self._state:
            return
        with self.driver_lock:
            cmd = QueryActualLevel(self.addr)
            r = self.driver.send(cmd)
            self._brightness = to_hass_level(r.value.as_integer)
        
        _LOGGER.debug("[{}] brightness = {} ".format(self._name, self._brightness)) 
 
