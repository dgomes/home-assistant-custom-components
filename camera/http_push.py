"""
Camera platform that receives images through HTTP POST.

For more details about this platform, please refer to the documentation
https://home-assistant.io/components/camera.http_push/
"""
import logging
import datetime

import homeassistant.util.dt as dt_util
import voluptuous as vol

from homeassistant.components.camera import Camera, PLATFORM_SCHEMA, DOMAIN,\
    STATE_IDLE, STATE_RECORDING, STATE_STREAMING
from homeassistant.core import callback
from homeassistant.components.http.view import HomeAssistantView
from homeassistant.const import CONF_NAME, HTTP_BAD_REQUEST
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.event import async_track_point_in_utc_time

_LOGGER = logging.getLogger(__name__)

API_URL = "/api/camera_http_push/{entity_id}"

DEFAULT_NAME = 'HTTP Push Camera'

BLANK_IMAGE_SIZE = (320, 240)

ATTR_LAST_MOTION = "last_motion"
ATTR_FILENAME = "filename"

REQUIREMENTS = ['pillow==5.0.0']

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend({
    vol.Optional(CONF_NAME, default=DEFAULT_NAME): cv.string
})


async def async_setup_platform(hass, config, async_add_devices,
                               discovery_info=None):
    """Set up the HTTP Push camera platform."""
    cameras = [HttpPushCamera(config.get(CONF_NAME))]

    hass.http.register_view(CameraPushReceiver(cameras))

    async_add_devices(cameras)


class CameraPushReceiver(HomeAssistantView):
    """Handle pushes from remote camera."""

    url = API_URL
    name = 'api:camera:http_push'

    def __init__(self, cameras):
        """Initialize CameraPushReceiver with camera entity."""
        self._cameras = cameras

    async def post(self, request, entity_id):
        """Accept the POST from Camera."""
        try:
            (_camera,) = [camera for camera in self._cameras
                          if camera.entity_id == entity_id]
        except ValueError:
            return self.json_message('Unknown HTTP Push Camera',
                                     HTTP_BAD_REQUEST)

        try:
            data = await request.post()
            _LOGGER.debug("Received Camera push: %s", data['image'])
            _camera.update_image(data['image'].file.read(), data['image'].filename)
        except ValueError:
            return self.json_message('Invalid POST', HTTP_BAD_REQUEST)


class HttpPushCamera(Camera):
    """The representation of a HTTP Push camera."""

    def __init__(self, name):
        """Initialize http push camera component."""
        super().__init__()
        self._name = name
        self._motion_status = False
        self._last_update = None
        self._filename = None
        self._expired = None
        self._state = STATE_IDLE
        self._period = datetime.timedelta(seconds=5) #TODO IDLE TIME

        from PIL import Image
        import io

        image = Image.new('RGB', BLANK_IMAGE_SIZE)

        imgbuf = io.BytesIO()
        image.save(imgbuf, "JPEG")

        self._current_image = imgbuf.getvalue()

    @property
    def state(self):
        return self._state

    def update_image(self, image, filename):
        """Update the camera image."""
        self._current_image = image
        self._last_update = dt_util.utcnow()
        self._filename = filename
        self._state = STATE_RECORDING

        @callback
        def reset_state(now):
            """Set state to off after no motion for a period of time."""
            self._state = STATE_IDLE 
            self.async_schedule_update_ha_state()
            self._expired = None

        if self._expired:
            self._expired()

        self._expired = async_track_point_in_utc_time(
            self.hass, reset_state, dt_util.utcnow() + self._period)

        self.schedule_update_ha_state()

        self.hass.bus.fire(DOMAIN, {
            'entity_id': self.entity_id,
            'filename': self._filename,
            'last_update': self._last_update,
            'name': self.name,
        })

    def camera_image(self):
        """Return a still image response."""
        return self._current_image

    async def async_camera_image(self):
        """Return a still image response."""
        return self.camera_image()

    @property
    def name(self):
        """Return the name of this camera."""
        return self._name

    @property
    def motion_detection_enabled(self):
        """Camera Motion Detection Status."""
        return self._motion_status

    @property
    def device_state_attributes(self):
        """Return the state attributes."""
        return {
            name: value for name, value in (
                (ATTR_LAST_MOTION, self._last_update),
                (ATTR_FILENAME, self._filename),
            ) if value is not None
        }
