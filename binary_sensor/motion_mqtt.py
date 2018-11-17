"""
Support for Custom Motion Sensor based in MQTT binary sensors.

"""
import logging

import voluptuous as vol

from homeassistant.core import callback
import homeassistant.components.mqtt as mqtt
from homeassistant.const import (
    CONF_FORCE_UPDATE, CONF_NAME, CONF_VALUE_TEMPLATE, CONF_PAYLOAD_ON,
    CONF_PAYLOAD_OFF)
from homeassistant.components.binary_sensor import ENTITY_ID_FORMAT
from homeassistant.components.mqtt import (
    CONF_STATE_TOPIC, CONF_AVAILABILITY_TOPIC, CONF_PAYLOAD_AVAILABLE,
    CONF_PAYLOAD_NOT_AVAILABLE, CONF_QOS, CONF_COMMAND_TOPIC)
from homeassistant.components.binary_sensor.mqtt import MqttBinarySensor
from homeassistant.helpers.entity import async_generate_entity_id
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.event import async_track_point_in_utc_time
from homeassistant.util import dt as dt_util

_LOGGER = logging.getLogger(__name__)

DEFAULT_NAME = 'Custom motion sensor'

CONF_PERIOD = 'period'

DEFAULT_PAYLOAD_OFF = 0
DEFAULT_PAYLOAD_ON = 1

DEPENDENCIES = ['mqtt']

PLATFORM_SCHEMA = mqtt.MQTT_RO_PLATFORM_SCHEMA.extend({
    vol.Optional(CONF_NAME, default=DEFAULT_NAME): cv.string,
    vol.Optional(CONF_PAYLOAD_OFF, default=DEFAULT_PAYLOAD_OFF): cv.string,
    vol.Optional(CONF_PAYLOAD_ON, default=DEFAULT_PAYLOAD_ON): cv.string,
    vol.Required(CONF_PERIOD): vol.All(cv.time_period, cv.positive_timedelta),
    vol.Optional(CONF_COMMAND_TOPIC): cv.string,
}).extend(mqtt.MQTT_AVAILABILITY_SCHEMA.schema)


async def async_setup_platform(hass, config, async_add_devices, discovery_info=None):
    """Set up the MQTT binary sensor."""
    if discovery_info is not None:
        config = PLATFORM_SCHEMA(discovery_info)

    value_template = config.get(CONF_VALUE_TEMPLATE)
    if value_template is not None:
        value_template.hass = hass

    async_add_devices([MotionSensor(hass,
                                    config.get(CONF_NAME),
                                    config.get(CONF_STATE_TOPIC),
                                    config.get(CONF_AVAILABILITY_TOPIC),
                                    config.get(CONF_QOS),
                                    config.get(CONF_FORCE_UPDATE),
                                    config.get(CONF_PAYLOAD_ON),
                                    config.get(CONF_PAYLOAD_OFF),
                                    config.get(CONF_PAYLOAD_AVAILABLE),
                                    config.get(CONF_PAYLOAD_NOT_AVAILABLE),
                                    value_template,
                                    config.get(CONF_PERIOD),
                                    config.get(CONF_COMMAND_TOPIC),
                                   )])


class MotionSensor(MqttBinarySensor):
    """Representation a binary sensor that is updated by MQTT."""

    def __init__(self, hass, name, state_topic, availability_topic,
                 qos, force_update, payload_on, payload_off, payload_available,
                 payload_not_available, value_template, period, command_topic):
        """Initialize the Motion sensor."""

        # Call father MqttBinarySensor
        super().__init__(name, state_topic, availability_topic, 'motion',
                         qos, force_update, payload_on, payload_off,
                         payload_available, payload_not_available,
                         value_template, unique_id=None, discovery_hash=None)

        # Fill the blanks
        self._period = period
        self._expired = None
        self._command_topic = command_topic
        self._entity_id = async_generate_entity_id(ENTITY_ID_FORMAT,
                                                   name, hass=hass)

        _LOGGER.debug("%s | period: %s", self._entity_id, period)

    async def async_added_to_hass(self):
        """Subscribe mqtt events."""
        await super(MqttBinarySensor, self).async_added_to_hass()

        @callback
        def reset_state(now):
            """Set state to off after no motion for a period of time."""
            _LOGGER.debug("reset_state for %s", self._entity_id)
            self._state = False
            self.async_schedule_update_ha_state()
            self._expired = None

        @callback
        def state_message_received(topic, payload, qos):
            """Handle a new received MQTT state message."""
            _LOGGER.debug("%s: %s", topic, payload)
            if self._template is not None:
                payload = self._template.async_render_with_possible_json_value(
                    payload)
            if payload == self._payload_on:
                self._state = True
                self.async_schedule_update_ha_state()
                if self._command_topic:
                    mqtt.async_publish(self.hass,
                                       self._command_topic,
                                       self._payload_off,
                                       self._qos)

                if self._expired:
                    self._expired()

                self._expired = async_track_point_in_utc_time(
                    self.hass, reset_state, dt_util.utcnow() + self._period)
            # ignore any other payloads

        await mqtt.async_subscribe(
            self.hass, self._state_topic, state_message_received, self._qos)
