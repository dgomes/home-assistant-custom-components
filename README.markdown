# Home-Assistant Custom Components
Some of my custom components for home-assistant (HA). (http://www.home-assistant.io)

* [Bluetooth Speaker](bluetooth_speaker/) - Play TTS through your bluetooth speaker connected to HA. (DEPRECATED)
* [DALI Light](dali/) - Control your DALI lights (DEPRECATED but forked and maintained by @rousveiga https://github.com/rousveiga/home-assistant-custom-components/tree/master/dali)
* [Developer](#developer) - Get notifications of HA Pull-Requests 
* [Electricity](electricity/) - Current tariff of a given electricity operator (DEPRECATED)
* [HomeGW Climate](#homegw-climate) - Use an RF433Mhz weather logger as a climate sensor
* [HomeGW Weather](#homegw-weather) - Use an RF433Mhz weather station
* [HomeGW Cover](#homegw-cover) - Control your covers with just two relay's

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

# HomeGW Cover

This is a **cover** platform on top of 2 relays exposed through MQTT. Each relays is closed for the duration in milliseconds publish to the control topic. **delay_time** indicates the time needed to go from 0% to 100% cover. Albeit the name, it is not related to the hardware supporting weather and climate components, for more information on this backend see [home_mqtt](https://github.com/dgomes/home_mqtt).

### Example configuration

```yaml
- platform: home_mqtt
  covers:
    living_room:
      relay_up: 1
      relay_down: 2
      delay_time: 17000
    suite:
      relay_up: 3
      relay_down: 4
      delay_time: 17000
```
