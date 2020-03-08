# DEPRECATED 
This custom_component has not been updated according to the most recent HA component guidelines, will therefore not work in the current version.
If you feel like fixing this component, let me know :) I will gladly accept PR's

# Bluetooth Speaker

This is a **media_player** platform that enables playback of _mp3_ and _wav_ files through a Bluetooth Speaker paired with a Linux Host using the [bluealsa](https://github.com/Arkq/bluez-alsa) stack.
This is the same to say: It works with my RPi3 running hassbian.

In order to use this _media\_player_ you must first setup bluealsa.
```bash
$ apt-get install bluez bluealsa
```

Afterwards, pair your bluetooth speaker using **bluetoothctl**, please refer to [https://ukbaz.github.io/howto/Bluetooth_speakers.html](https://ukbaz.github.io/howto/Bluetooth_speakers.html)

Last you configure alsa settings for the user running home-assistant, please adapt according to your devices.

```bash
$ cat ~/.asoundrc
defaults.bluealsa.interface "hci0"
defaults.bluealsa.device "XX:XX:XX:XX:XX:XX"
defaults.bluealsa.profile "a2dp"
```

## Example configuration

```yaml
media_player:
- platform: bluetooth_speaker
  name: My Bluetooth Speaker #OPTIONAL
  device: 'OEM Speaker' #REQUIRED: this string is what shows up when you discover a new device
  step: 0.05 #OPTIONAL: steps increase/decrease volume
  cache_dir: /tmp/tts #OPTIONAL: only matters if you're not using the default
```

#
