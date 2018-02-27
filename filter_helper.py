"""Filter helpers for Home Assistant."""
import logging
import inspect

from sensor.filter import (
    OutlierFilter, LowPassFilter, ThrottleFilter)

FILTER_LOWPASS = 'lowpass'
FILTER_OUTLIER = 'outlier'

FILTERS = {
            FILTER_LOWPASS: LowPassFilter,
            FILTER_OUTLIER: OutlierFilter
          }

class Filter(object):
    """Filter decorator."""
    def __init__(self, filter_algorithm, **kwargs):
        """Decorator constructor, selects algorithm and configures window.
        Args:
            filter_algorithm (string): must be one of the defined filters
            window_size (int): size of the sliding window that holds previous
                                values
            kwargs (dict): arguments to be passed to the specific filter
        """
        module_name = inspect.getmodule(inspect.stack()[1][0]).__name__
        Filter.logger = logging.getLogger(module_name)
        Filter.logger.debug("Filter %s(%s) on %s", filter_algorithm, kwargs,
                            module_name)
        self.filter_args = kwargs

        if filter_algorithm in FILTERS:
            Filter.logger.debug("%s(%s)", filter_algorithm, kwargs)
            self.filter = FILTERS[filter_algorithm](**kwargs)
        else:
            self.logger.error("Unknown filter <%s>", filter_algorithm)
            return

    def __call__(self, func):
        """Decorate function as filter."""
        def func_wrapper(sensor_object):
            """Wrap for the original state() function."""
            Filter.sensor_name = sensor_object.entity_id
            self.filter._entity = Filter.sensor_name
            new_state = func(sensor_object)
            try:
                filtered_state = self.filter.filter_state(new_state)
            except TypeError:
                return None

            Filter.logger.debug("%s(%s) -> %s", self.filter._entity,
                                new_state, filtered_state)
            return filtered_state

        return func_wrapper
