
class ArrayContext(object):
    """
    Array context stores the config and the state of an
    array during job processing
    """
    # array config
    ID = "id"
    API_TOKEN = "api_token"
    NAME = "name"
    HOST = "host"
    PURITY_VERSION = "purity_version"

    # collection config
    FREQUENCY = "frequency"
    ENABLED = "enabled"
    DATA_TTL = "data_ttl"

    # Execution values coming from job processing
    TASK_TIMESTAMP = "task_timestamp"
    TASK_STATE = "task_state"

    # Default polling frequency is 60 sec
    DEFAULT_FREQUENCY = 60

    def __init__(self):
        self._config_json = {}
        self._task = None
        self._task_starttime = 0
        self._task_state = None

    @property
    def id(self):
        return self._config_json[ArrayContext.ID] if ArrayContext.ID in self._config_json else None

    @id.setter
    def id(self, value):
        self._config_json[ArrayContext.ID] = value

    @property
    def purity_version(self):
        return self._config_json[ArrayContext.PURITY_VERSION] if ArrayContext.PURITY_VERSION in self._config_json else None

    @id.setter
    def purity_version(self, value):
        self._config_json[ArrayContext.PURITY_VERSION] = value

    @property
    def name(self):
        return self._config_json[ArrayContext.NAME] if ArrayContext.NAME in self._config_json else None

    @name.setter
    def name(self, value):
        self._config_json[ArrayContext.NAME] = value

    @property
    def api_token(self):
        return self._config_json[ArrayContext.API_TOKEN] if ArrayContext.API_TOKEN in self._config_json else None

    @api_token.setter
    def api_token(self, value):
        self._config_json[ArrayContext.API_TOKEN] = value

    @property
    def host(self):
        return self._config_json[ArrayContext.HOST] if ArrayContext.HOST in self._config_json else None

    @property
    def enabled(self):
        # Default to enabled.
        return self._config_json[ArrayContext.ENABLED] if ArrayContext.ENABLED in self._config_json else True

    @property
    def data_ttl(self):
        # Default to None, i.e. no data retention.
        return self._config_json[ArrayContext.DATA_TTL] if ArrayContext.DATA_TTL in self._config_json else None

    @property
    def frequency(self):
        return int(self._config_json[ArrayContext.FREQUENCY]) \
            if ArrayContext.FREQUENCY in self._config_json \
            else ArrayContext.DEFAULT_FREQUENCY

    @property
    def task(self):
        return self._task

    @task.setter
    def task(self, value):
        self._task = value

    @property
    def task_state(self):
        # If there is a task object, we get the latest state from the task.
        # otherwise, we get the cached state retrieved from deserialization.
        return self.task.state if self.task is not None else self._task_state

    @task_state.setter
    def task_state(self, value):
        # Use when deserializing the state from file
        self._task_state = value

    @property
    def task_starttime(self):
        return self._task_starttime

    @task_starttime.setter
    def task_starttime(self, value):
        self._task_starttime = value

    @property
    def is_task_completed(self):
        return self.task is None or self.task.state == "FAILURE" or self.task.state == "SUCCESS"

    def get_config_json(self):
        """
        Return the config of the Array in json
        :return: The json config of the array
        """
        return self._config_json

    def update_config_json(self, json):
        """
        Update the array's config from the input json.
        :param json:
        :return:
        """
        self._config_json.update(json)

    def get_state_json(self):
        """
        Return the state of the array's execution in json
        :return:
        """
        return {
            ArrayContext.ID: self.id,
            ArrayContext.TASK_TIMESTAMP: self.task_starttime,
            ArrayContext.TASK_STATE: self.task_state
        }

    def update_state_json(self, json):
        """
        Update the state of the array. Used in repopulating the state from internal store.
        :param json:
        :return:
        """
        self.task_starttime = json[ArrayContext.TASK_TIMESTAMP]
        self.task_state = json[ArrayContext.TASK_STATE]

    def get_json(self):
        """
        Return a json object combining both state information and config information
        :return:
        """
        # Merge both config and state into one json.
        result = self.get_config_json()
        result.update(self.get_state_json())
        return result
