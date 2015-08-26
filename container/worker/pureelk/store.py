import json
import os
import urllib

from pureelk.arraycontext import ArrayContext

STATE_FILE = ".pureelk.arrays.state"

class Store(object):

    def __init__(self, path, logger):
        """
        Store class for saving and loading of states
        The current implementation is file-based since the data set is tiny
        Each array's config is stored in its own .json file. The worker also
        write the current task state into a .pureelk.state file each time it runs.
        :param path: The path of the folder containing all the configs
        :return: dictionary of arrays, index by array id.
        """
        self._path = path
        self._logger = logger

    def load_arrays(self):
        arrays = {}

        # Load all the json configs for the arrays.
        for file_name in os.listdir(self._path):
            if file_name.endswith(".json"):
                try:
                    array = self._load_config_one(file_name)
                    arrays[array.id] = array
                except Exception as e:
                    self._logger.warn("Exception at loading config {}: {}".format(file_name, e))

        try:
            # Load the arrays execution state and merge them in.
            for array_state in self._load_state():
                array_id = array_state[ArrayContext.ID]
                if array_id in arrays:
                    arrays[array_id].update_state_json(array_state)
        except Exception as e:
            self._logger.warn("Exception at loading execution state {}".format(e))

        return arrays

    def save_array_states(self, arrays):
        with open(os.path.join(self._path, STATE_FILE), 'w') as state_file:
            state_file.write(json.dumps([a.get_state_json() for a in arrays]))

    def save_array_config(self, array):
        file_name = os.path.join(self._path, urllib.unquote(array.id) + ".json")
        with open(file_name, "w") as config_file:
            config_file.write(json.dumps(array.get_config_json()))

    def remove_array_config(self, id):
        file_name = os.path.join(self._path, urllib.unquote(id) + ".json")
        try:
            os.remove(file_name)
        except OSError as error:
            self._logger.warn("Error when removing array '{}': {}".format(id, error))

    def _load_config_one(self, filename):
        path = os.path.join(self._path, filename)
        if os.path.exists(path):
            array = ArrayContext()
            with open(path) as json_file:
                json_object = json.load(json_file)
                array.update_config_json(json_object)
                # TODO: We use file name as id if it is not present in the JSON.
                if not array.id:
                    array.id = urllib.quote(os.path.splitext(filename)[0])
                self._logger.info("Loaded config = {}".format(json_object))

            return array

        raise ValueError("Array config {} not found".format(filename))

    def _load_state(self):
        path = os.path.join(self._path, STATE_FILE)
        state = []
        self._logger.info("loading state from {}".format(path))
        if os.path.exists(path):
            with open(path) as state_file:
                state = json.load(state_file)
                self._logger.info("Loaded state = {}".format(state))

        return state
