# Home-Assistant Custom Components
Some of my custom components for home-assistant (HA). (http://www.home-assistant.io)

* [Developer](#developer) - Get notifications of HA Pull-Requests
* [HomeGW Climate](#homegw-climate) - Use an RF433Mhz weather logger as a climate sensor
* [HomeGW Weather](#homegw-weather) - Use an RF433Mhz weather station
* [Bluetooth Speaker](#bluetooth-speaker) - Play TTS through your bluetooth speaker connected to HA.

## Developer

As a Home Assistant developer, I like to keep a close eye into whats new (Pull Requests - PR). This component uses github API to find PR related to the components currently in use in the running HA.

```yaml
developer:
  github_personal_token: "1231231e23442342312312312312"
```
You can get your own personal token [here](https://github.com/settings/tokens)

## HomeGW Climate

I'm currently using a cheap [433MHz Wireless sensor](https://www.banggood.com/Digoo-DG-R8H-433MHz-Wireless-Digital-Hygrometer-Thermometer-Weather-Station-Sensor-for-TH11300-8380-p-1178108.html?utm_source=google&utm_medium=cpc_elc&utm_campaign=ds-indu-sw1&utm_content=mandy&gclid=CjwKCAiA_c7UBRAjEiwApCZi8UAms95tLkgCzClVfbSxz7hbadrRKku94AhHCsKtQGwaZzlVXK2e2BoCs8YQAvD_BwE&cur_warehouse=CN) to monitor several rooms in the house.

Attached to my RPi3 running HA I've got an [Arduino working as a gateway](http://diogogomes.com/2012/07/05/arduino-rf-ir-remote-control/index.html). The code running in the Arduino is provided [here](https://github.com/dgomes/homegw). 

The serial sensor receives a payload similar to:
```json
{"dev":"digoo","id":8,"ch":3,"batt":1,"temp":20,"hum":56,"raw":"0x8a0c8f38"}
```

Using the [serial sensor](https://home-assistant.io/components/sensor.serial/) platform and a [MQTT binary sensor](https://home-assistant.io/components/binary_sensor.mqtt/) I've created the [homegw_climate](https://github.com/dgomes/home-assistant-custom-components/blob/master/climate/homegw_climate.py) custom component that looks like a thermostat, but cannot act upon the HVAC.

The platform supports filtering by channel (ch) which is the only parameter the device provides configuration for.

## HomeGW Weather

The weather station is by all means a copy of the climate platform (or the other way round). The same serial sensor is monitored, only the Wireless sensor is different.

### Example configuration

```yaml

sensor:
  - platform: serial
    serial_port:  /dev/tty.USB0
    baudrate: 115200
    
binary_sensor:
  - platform: mqtt
    state_topic: "devices/heating/status"
    name: heating
    device_class: heat

climate:
  - platform: homegw_climate
    name: quarto2
    serial_sensor: sensor.serial_sensor
    heating_sensor: binary_sensor.heating
    channel: 2

weather:
  - platform: homegw_weather
    name: backyard
    serial_sensor: sensor.serial_sensor
```

# The *filter_helper.py*

This file provides a decorator class used in the homegw_climate and homegw_weather platforms. It has a dependency in the [filter sensor](https://www.home-assistant.io/components/sensor.filter/) which actually implements the filters.

### Example configuration

```yaml

binary_sensor:
  - platform: motion_mqtt
    name: test_cozinha
    state_topic: devices/sonoff_rfbridge/relay/0
    command_topic: devices/sonoff_rfbridge/relay/0/set
    availability_topic: devices/sonoff_rfbridge/status
    payload_available: 1
    payload_not_available: 0
    period: 5:00

```

## Bluetooth Speaker

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

### Example configuration

```yaml
media_player:
- platform: bluetooth_speaker
  name: My Bluetooth Speaker #OPTIONAL
  device: 'OEM Speaker' #REQUIRED: this string is what shows up when you discover a new device
  step: 0.05 #OPTIONAL: steps increase/decrease volume
  cache_dir: /tmp/tts #OPTIONAL: only matters if you're not using the default
```
