# Electricity

This component provides the current tariff of a given electricity operator 

Although this component can work alone, it was built as a complement to the [utility_meter component](https://github.com/dgomes/home-assistant-custom-components/tree/master/utility_meter). Integration between both is achieved through state sincronization using an automation.

## Configuration example

```yaml
electricity:
  home:
    country: Portugal
    operator: EDP
    plan: Bi-horário - ciclo diário

automation:
  - alias: tariff change
    trigger:
      - platform: state
        entity_id: electricity.<operator_plan>
    action:
      - service: utility_meter.select_tariff
        entity_id: utility_meter.<energy>
        data_template:
          tariff: "{{ trigger.to_state.state }}" 
```

## Supported Plans

Go to https://github.com/dgomes/python-electricity/blob/master/README.md
