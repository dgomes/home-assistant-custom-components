"""
Support for lights controlled by home_mqtt.

More information in https://github.com/dgomes/home_mqtt

"""
import asyncio
import logging

import voluptuous as vol

import homeassistant.components.mqtt as mqtt
from homeassistant.components.light import Light
from homeassistant.const import (
    CONF_OPTIMISTIC,
    CONF_NAME, CONF_PAYLOAD_OFF, CONF_PAYLOAD_ON, STATE_ON)
from homeassistant.components.mqtt import (
    CONF_AVAILABILITY_TOPIC, CONF_PAYLOAD_AVAILABLE,
    CONF_PAYLOAD_NOT_AVAILABLE, CONF_QOS, CONF_COMMAND_TOPIC,
    MqttAvailability)
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.restore_state import async_get_last_state

_LOGGER = logging.getLogger(__name__)

DEPENDENCIES = ['mqtt']

CONF_RELAY = 'relay'

COMMAND_FORMAT = '{}/{}'

DEFAULT_NAME = 'Home MQTT Light'
DEFAULT_OPTIMISTIC = False

PLATFORM_SCHEMA = mqtt.MQTT_RW_PLATFORM_SCHEMA.extend({
    vol.Optional(CONF_NAME, default=DEFAULT_NAME): cv.string,
    vol.Required(CONF_RELAY): cv.positive_int,
    vol.Required(CONF_PAYLOAD_OFF): cv.positive_int,
    vol.Required(CONF_PAYLOAD_ON): cv.positive_int,
    vol.Optional(CONF_OPTIMISTIC, default=DEFAULT_OPTIMISTIC): cv.boolean,
}).extend(mqtt.MQTT_AVAILABILITY_SCHEMA.schema)


async def async_setup_platform(hass, config, async_add_devices, discovery_info=None):
    """Set up a MQTT Light."""
    if discovery_info is not None:
        config = PLATFORM_SCHEMA(discovery_info)

    async_add_devices([HomeMqttLight(
        config.get(CONF_NAME),
        COMMAND_FORMAT.format(config.get(CONF_COMMAND_TOPIC), config.get(CONF_RELAY)),
        config.get(CONF_QOS),
        {
            'on': config.get(CONF_PAYLOAD_ON),
            'off': config.get(CONF_PAYLOAD_OFF),
        },
        config.get(CONF_OPTIMISTIC),
        config.get(CONF_AVAILABILITY_TOPIC),
        config.get(CONF_PAYLOAD_AVAILABLE),
        config.get(CONF_PAYLOAD_NOT_AVAILABLE),
    )])


class HomeMqttLight(MqttAvailability, Light):
    """Representation of a MQTT light."""

    def __init__(self, name, topic, qos, payload, optimistic,
                 availability_topic, payload_available, payload_not_available):
        """Initialize MQTT light."""
        super().__init__(availability_topic, qos, payload_available,
                         payload_not_available)
        self._name = name
        self._topic = topic
        self._qos = qos
        self._payload = payload
        self._optimistic = optimistic
        self._state = False

    async def async_added_to_hass(self):
        """Subscribe to MQTT events."""
        await super().async_added_to_hass()

        state = await async_get_last_state(self.hass, self.entity_id)
        if state:
            self._state = state.state == STATE_ON

    @property
    def assumed_state(self):
        """Return true if we do optimistic updates."""
        return self._optimistic

    @property
    def should_poll(self):
        """No polling needed for a MQTT light."""
        return False

    @property
    def name(self):
        """Return the name of the device if any."""
        return self._name

    @property
    def is_on(self):
        """Return true if device is on."""
        return self._state

    @property
    def assumed_state(self):
        """Return true if we do optimistic updates."""
        return self._optimistic 

    async def async_turn_on(self, **kwargs):
        """Turn the device on.

        This method is a coroutine.
        """

        mqtt.async_publish(
            self.hass, self._topic+'/set',
            self._payload['on'], self._qos)

        # Optimistically assume that switch has changed state.
        self._state = True
        self.async_schedule_update_ha_state()

    async def async_turn_off(self, **kwargs):
        """Turn the device off.

        This method is a coroutine.
        """
        mqtt.async_publish(
            self.hass, self._topic+'/set',
            self._payload['off'], self._qos)

        # Optimistically assume that switch has changed state.
        self._state = False
        self.async_schedule_update_ha_state()
