"""Support for a Bluetooth Speaker connected to a RPi3."""
import os
import shlex
import subprocess
import logging
import voluptuous as vol
from homeassistant.components.media_player import (
    SUPPORT_PLAY_MEDIA,
    SUPPORT_VOLUME_MUTE,
    SUPPORT_VOLUME_SET,
    SUPPORT_VOLUME_STEP,
    PLATFORM_SCHEMA,
    MediaPlayerDevice)
from homeassistant.const import (
    CONF_NAME, STATE_ON, STATE_PLAYING)
import homeassistant.helpers.config_validation as cv


REQUIREMENTS = ['pyalsaaudio==0.8.4']

DEFAULT_NAME = 'RPi3 Bluetooth Speaker'
DEFAULT_VOLUME = 0.5
DEFAULT_VOLUME_STEP = 0.05
DEFAULT_CACHE_DIR = "tts"

CONF_DEVICE_NAME = 'device'
CONF_VOLUME = 'volume'
CONF_VOLUME_STEP = 'volume_step'
CONF_CACHE_DIR = 'cache_dir'

MP3_CMD = "mpg123 -q -a bluealsa"
WAV_CMD = "aplay -q -a bluealsa"

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend({
    vol.Optional(CONF_NAME, default=DEFAULT_NAME): cv.string,
    vol.Required(CONF_DEVICE_NAME): cv.string,
    vol.Optional(CONF_VOLUME_STEP, default=DEFAULT_VOLUME_STEP):
        vol.All(vol.Coerce(float), vol.Range(min=0.01, max=1)),
    vol.Optional(CONF_CACHE_DIR, default=DEFAULT_CACHE_DIR): cv.string,
})

_LOGGER = logging.getLogger(__name__)


def setup_platform(hass, config, add_devices, discovery_info=None):
    """Setup the Bluetooth Speaker platform."""
    name = config.get(CONF_NAME)
    device_name = config[CONF_DEVICE_NAME]
    step = config.get(CONF_VOLUME_STEP)

    cache_dir = config.get(CONF_CACHE_DIR)
    if not os.path.isabs(cache_dir):
        cache_dir = hass.config.path(cache_dir)

    add_devices([BluetoothSpeakerDevice(name,
                                        device_name,
                                        step,
                                        cache_dir)])
    return True


class BluetoothSpeakerDevice(MediaPlayerDevice):
    """Representation of a Bluetooth Speaker on the network."""

    def __init__(self, name, device_name, step, cache_dir):
        """Initialize the device."""
        self._name = name
        self._device_name = device_name
        self._is_standby = True
        self._step = step
        self._cache_dir = cache_dir
        self._volume = 0
        self._muted = False
        self._proc = None
        self.mixer = None

    def _set_mixer(self):
        import alsaaudio

        for _mixer in alsaaudio.mixers(device="bluealsa"):
            if self._device_name in _mixer:
                _LOGGER.info("Using Bluetooth Speaker %s", _mixer)
                self.mixer = alsaaudio.Mixer(_mixer, device="bluealsa")

    def update(self):
        """Retrieve latest state."""
        if not self.mixer:
            self._set_mixer()
        self._volume = float(self.mixer.getvolume()[0])/100
        self._muted = True if 1 in self.mixer.getmute() else False

        if self._proc:
            self._proc.poll()
            if self._proc.returncode is not None:
                self._is_standby = True
                self._proc = None

    @property
    def name(self):
        """Return the name of the device."""
        return self._name

    # MediaPlayerDevice properties and methods
    @property
    def state(self):
        """Return the state of the device."""
        if self._is_standby:
            return STATE_ON
        return STATE_PLAYING

    @property
    def supported_features(self):
        """Flag media player features that are supported."""
        return SUPPORT_VOLUME_MUTE | SUPPORT_VOLUME_SET\
            | SUPPORT_VOLUME_STEP | SUPPORT_PLAY_MEDIA

    @property
    def volume_level(self):
        """Volume level of the media player (0..1)."""
        return self._volume

    @property
    def is_volume_muted(self):
        """Boolean if volume is currently muted."""
        return self._muted

    def set_volume_level(self, volume):
        """Set volume level, range 0..1."""
        import alsaaudio

        self._volume = volume
        self.mixer.setvolume(int(volume*100), alsaaudio.MIXER_CHANNEL_ALL)

    def mute_volume(self, mute):
        """Mute the volume."""
        import alsaaudio

        self._muted = mute
        self.mixer.setmute(1 if mute else 0, alsaaudio.MIXER_CHANNEL_ALL)

    def volume_up(self):
        """Volume up media player."""
        self.set_volume_level(self._volume+self._step)

    def volume_down(self):
        """Volume down media player."""
        self.set_volume_level(self._volume-self._step)

    def media_pause(self):
        if self._proc:
            self._proc.terminate()
            self._proc = None
        self._is_standby = True

    def play_media(self, media_type, media_id, **kwargs):
        """Send play commmand."""
        _LOGGER.debug('play_media: %s, %s', media_type, media_id)

        if not self._is_standby:
            self.media_pause()

        self._is_standby = False
        
        media_content = media_id

        media_file = self._cache_dir+'/'+media_id[media_id.rfind('/')+1:]
        if os.path.isfile(media_file):
            #Avoid http proxy
            media_content = media_file
        else:
            command = MP3_CMD #if its an url its likely to be an MP3

        if media_content[-3:].lower() == "mp3":
            command = MP3_CMD
        elif media_content[-3:].lower() == "wav":
            command = WAV_CMD
        else:
            _LOGGER.error("Don't know how to handle %s, probably mpg123 can handle it", media_content)

        command += " {content}".format(content=media_content)
        _LOGGER.debug('Executing command: %s', command)
        args = shlex.split(command)
        self._proc = subprocess.Popen(args)
