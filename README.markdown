# Home-Assistant Custom Components
Some of my custom components for home-assistant (HA). (http://www.home-assistant.io)

* [Bluetooth Speaker](bluetooth_speaker/) - Play TTS through your bluetooth speaker connected to HA. (DEPRECATED)
* [DALI Light](dali/) - Control your DALI lights (DEPRECATED but forked and maintained by @rousveiga https://github.com/rousveiga/home-assistant-custom-components/tree/master/dali)
* [Developer](#developer) - Get notifications of HA Pull-Requests (NOT MAINTAINED)
* [Electricity](electricity/) - Current tariff of a given electricity operator (DEPRECATED)
* [Home Assistant ERSE](ha_erse/) - Track the current tariff and automates utility_meters (replaces [Electricity] and is available on [HACS](https://hacs.xyz))
* [HomeGW Climate](homegw/) - Use an RF433Mhz weather logger as a climate sensor
* [HomeGW Weather](homegw/) - Use an RF433Mhz weather station
* [HomeGW Cover](homegw/) - Control your covers with just two relay's
* [RRD Recorder](rrd_recorder/) - Store historical data efficently using Round-Robin-Database (available on [HACS](https://hacs.xyz))

## Developer

As a Home Assistant developer, I like to keep a close eye into whats new (Pull Requests - PR). This component uses github API to find PR related to the components currently in use in the running HA.

```yaml
developer:
  github_personal_token: "1231231e23442342312312312312"
```
You can get your own personal token [here](https://github.com/settings/tokens)


# The *filter_helper.py*

This file provides a decorator class used in the homegw_climate and homegw_weather platforms. It has a dependency in the [filter sensor](https://www.home-assistant.io/components/sensor.filter/) which actually implements the filters.

