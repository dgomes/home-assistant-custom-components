# Home-Assistant Custom Components
Some of my custom components for home-assistant (HA). (http://www.home-assistant.io)

## HomeGW Climate

I'm currently using a cheap [433MHz Wireless sensor](https://www.banggood.com/Digoo-DG-R8H-433MHz-Wireless-Digital-Hygrometer-Thermometer-Weather-Station-Sensor-for-TH11300-8380-p-1178108.html?utm_source=google&utm_medium=cpc_elc&utm_campaign=ds-indu-sw1&utm_content=mandy&gclid=CjwKCAiA_c7UBRAjEiwApCZi8UAms95tLkgCzClVfbSxz7hbadrRKku94AhHCsKtQGwaZzlVXK2e2BoCs8YQAvD_BwE&cur_warehouse=CN) to monitor several rooms in the house.

Using the [serial sensor](https://home-assistant.io/components/sensor.serial/) platform and a [MQTT binary sensor](https://home-assistant.io/components/binary_sensor.mqtt/) I've created this custom component that looks like a thermostat, but cannot act upon the HVAC.

Attached to my RPi3 running HA I've got an [Arduino working as a gateway](http://diogogomes.com/2012/07/05/arduino-rf-ir-remote-control/index.html). The code running in the Arduino is provided [here](https://github.com/dgomes/homegw). 

The serial sensor receives a payload similar to:
```json
{"dev":"digoo","id":8,"ch":3,"batt":1,"temp":20,"hum":56,"raw":"0x8a0c8f38"}
```

The platform supports filtering by channel (ch) which is the only parameter the device provides configuration for.

## HomeGW Weather

The weather station is by all means a copy of the climate platform (or the other way round). The same serial sensor is monitored, just the Wireless sensor is different.

## Example configuration

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