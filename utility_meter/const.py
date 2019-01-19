"""Constants for the utility meter component."""
DOMAIN = 'utility_meter'

HOURLY = 'hourly'
DAILY = 'daily'
WEEKLY = 'weekly'
MONTHLY = 'monthly'
YEARLY = 'yearly'

METER_TYPES = [HOURLY, DAILY, WEEKLY, MONTHLY, YEARLY]

DATA_UTILITY = 'utility_meter_data'
UTILITY_COMPONENT = 'component'

CONF_METER = 'meter'
CONF_SOURCE_SENSOR = 'source'
CONF_METER_TYPE = 'cycle'
CONF_METER_OFFSET = 'offset'
CONF_PAUSED = 'paused'
CONF_TARIFFS = 'tariffs'
CONF_TARIFF = 'tariff'
CONF_TARIFF_ENTITY = 'tariff_entity'

SIGNAL_START_PAUSE_METER = 'utility_meter_start_pause'
SIGNAL_RESET_METER = 'utility_meter_reset'
