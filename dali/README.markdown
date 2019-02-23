# DALI Light

This is a **light** platform that will setup your DALI lights. The platform relies on [python-dali](https://github.com/sde1000/python-dali) and has only been tested with the [hasseb DALI master](http://hasseb.fi/shop2/index.php?route=product/product&product_id=50) (therefore no configuration available for other controllers). The platform will discover all your DALI lights and create entities for each ballast. For a faster discovery, declare `max_gears` with the total number of DALI lights in your setup.

## Example configuration
```yaml
- platform: dali
  name: Living Room
  max_gears: 4
```
