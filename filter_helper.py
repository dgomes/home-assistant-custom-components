"""Filter helpers for Home Assistant."""
import logging
import inspect

from homeassistant.components.filter.sensor import (
    OutlierFilter, LowPassFilter, ThrottleFilter,
    TimeSMAFilter, FilterState)
import homeassistant.util.dt as dt_util 


FILTER_LOWPASS = 'lowpass'
FILTER_OUTLIER = 'outlier'
FILTER_TIME_SMA = 'time_sma'
FILTER_THROTTLE = 'throttle'

FILTERS = {
    FILTER_LOWPASS: LowPassFilter,
    FILTER_OUTLIER: OutlierFilter,
    FILTER_TIME_SMA: TimeSMAFilter, 
    FILTER_THROTTLE: ThrottleFilter
    }

class FakeState(object):
    """Fake HA state."""
    def __init__(self, value):
        """Keep value and timestamp."""
        self.last_updated = dt_util.utcnow() 
        self.state = value

class Filter(object):
    """Filter decorator."""

    def __init__(self, filter_algorithm, **kwargs):
        """Decorator constructor, selects algorithm and configures window.

        Args:
            filter_algorithm (string): must be one of the defined filters
            kwargs (dict): arguments to be passed to the specific filter
        """
        try:
            module_name = inspect.stack()[1][0].f_globals['__name__']
            Filter.logger = logging.getLogger(module_name)
            Filter.logger.debug("Filter %s(%s) on %s", filter_algorithm, kwargs,
                                module_name)
        except:
            Filter.logger = logging.getLogger("custom_components")

        if filter_algorithm in FILTERS:
            self.filter = FILTERS[filter_algorithm](**kwargs)
        else:
            self.logger.error("Unknown filter <%s>", filter_algorithm)

    def __call__(self, func):
        """Decorate function as filter."""
        def func_wrapper(sensor_object):
            """Wrap for the original state() function."""
            new_state = FakeState(func(sensor_object))
            try:
                filtered_state = self.filter.filter_state(new_state)
            except TypeError:
                return None

            Filter.logger.debug("%s(%s) -> %s", sensor_object.entity_id,
                                new_state.state, filtered_state.state)
            return filtered_state.state

        return func_wrapper
