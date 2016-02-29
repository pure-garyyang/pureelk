
"""
    The global execution context of the worker
"""
from celery.utils.log import get_task_logger
from .store import Store

logger = get_task_logger(__name__)


class Context(object):
    def __init__(self, path):
        self._array_contexts = {}
        self._monitor_contexts = {}
        self._store = Store(path, logger)

    def prepare_arrays(self):
        new_arrays = self._store.load_arrays()
        arrays_not_refreshed = self._array_contexts.keys()

        logger.info("Reloaded configs. existing arrays are {}, new arrays are {}".format(
            arrays_not_refreshed,
            new_arrays.keys()))

        # Update the current execution context based on the  config store.
        for new_array in new_arrays.values():
            if new_array.id in self._array_contexts:
                # If the array already exists, we update its config.
                self._array_contexts[new_array.id].update_config_json(new_array.get_config_json())
                arrays_not_refreshed.remove(new_array.id)
            else:
                # If the array does not exist, we add it into the array_contexts.
                self._array_contexts[new_array.id] = new_array

        # For arrays no longer exists in the config store, we remove it from the context
        for array_id in arrays_not_refreshed:
            del self._array_contexts[array_id]

        logger.info("Arrays for collections = {}".format(self.array_contexts.keys()))
        self._store.save_array_states(self.array_contexts.values())

    def prepare_monitors(self):
        new_monitors = self._store.load_monitors()
        monitors_not_refreshed = self._monitor_contexts.keys()

        logger.info("Reloaded configs. existing monitors are {}, new monitors are {}".format(
            monitors_not_refreshed,
            new_monitors.keys()))

        # Update the current execution context based on the  config store.
        for new_monitor in new_monitors.values():
            if new_monitor.id in self._monitor_contexts:
                # If the monitor already exists, we update its config.
                self._monitor_contexts[new_monitor.id].update_config_json(new_monitor.get_config_json())
                monitors_not_refreshed.remove(new_monitor.id)
            else:
                # If the monitor does not exist, we add it into the monitor_contexts.
                self._monitor_contexts[new_monitor.id] = new_monitor

        # For monitors no longer exists in the config store, we remove it from the context
        for monitor_id in monitors_not_refreshed:
            del self._monitor_contexts[monitor_id]

        logger.info("monitors = {}".format(self._monitor_contexts.keys()))
        self._store.save_monitor_states(self._monitor_contexts.values())



    @property
    def array_contexts(self):
        return self._array_contexts

    @property
    def monitor_contexts(self):
        return self._monitor_contexts

