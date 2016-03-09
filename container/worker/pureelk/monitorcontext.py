

class MonitorContext(object):
    """
    Monitor context stores the config and the state of an
    monitor during job processing
    """
    # monitor config
    ID = "id"
    
    #optional name of the monitor
    NAME = "name"

    #parts of the query
    ARRAY_NAME = "array_name"
    VOL_NAME = "vol_name"
    COMPARE = "compare"
    WINDOW = "window"
    METRIC = "metric"
    VALUE = "value"
    HITS = "hits"
    TYPE = "type"
    SEVERITY = "severity"

    DEFAULT_SEVERITY = 'info'

    # collection config
    FREQUENCY = "frequency" # In seconds
    ENABLED = "enabled"
    DATA_TTL = "data_ttl"   # This follows the elastic search spec, e.g. "90d" is 90 days.

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
        return self._config_json[MonitorContext.ID]

    @id.setter
    def id(self, value):
        self._config_json[MonitorContext.ID] = value

    @property
    def name(self):
        return self._config_json[MonitorContext.NAME] if MonitorContext.NAME in self._config_json else ""

    @name.setter
    def name(self, value):
        self._config_json[MonitorContext.NAME] = value

    @property
    def enabled(self):
        # Default to enabled.
        return self._config_json[MonitorContext.ENABLED] if MonitorContext.ENABLED in self._config_json else True

    @property
    def array_name(self):
        return self._config_json[MonitorContext.ARRAY_NAME] if MonitorContext.ARRAY_NAME in self._config_json else None

    @property
    def vol_name(self):
        return self._config_json[MonitorContext.VOL_NAME] if MonitorContext.VOL_NAME in self._config_json else None

    @property
    def window(self):
        return self._config_json[MonitorContext.WINDOW] if MonitorContext.WINDOW in self._config_json else None

    @property
    def compare(self):
        return self._config_json[MonitorContext.COMPARE] if MonitorContext.COMPARE in self._config_json else None

    @property
    def metric(self):
        return self._config_json[MonitorContext.METRIC] if MonitorContext.METRIC in self._config_json else None

    @property
    def value(self):
        return int(self._config_json[MonitorContext.VALUE]) if MonitorContext.VALUE in self._config_json else None

    @property
    def severity(self):
        #default to info alert 
        return self._config_json[MonitorContext.SEVERITY] if MonitorContext.SEVERITY in self._config_json else MonitorContext.DEFAULT_SEVERITY

    @property
    def hits(self):
        # Default to None, i.e. no data retention.
        return int(self._config_json[MonitorContext.HITS]) if MonitorContext.HITS in self._config_json else None

    @property
    def type(self):
        # Default to None, i.e. no data retention.
        return self._config_json[MonitorContext.TYPE] if MonitorContext.TYPE in self._config_json else None


    @property
    def data_ttl(self):
        # Default to 30 days
        return self._config_json[MonitorContext.DATA_TTL] if MonitorContext.DATA_TTL in self._config_json else '30d'

    @property
    def frequency(self):
        return int(self._config_json[MonitorContext.FREQUENCY]) \
            if MonitorContext.FREQUENCY in self._config_json \
            else MonitorContext.DEFAULT_FREQUENCY


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
        Return the config of the monitor in json
        :return: The json config of the monitor
        """
        return self._config_json

    def update_config_json(self, json):
        """
        Update the monitor's config from the input json.
        :param json:
        :return:
        """
        self._config_json.update(json)

    def get_state_json(self):
        """
        Return the state of the monitor's execution in json
        :return:
        """
        return {
            MonitorContext.ID: self.id,
            MonitorContext.TASK_TIMESTAMP: self.task_starttime,
            MonitorContext.TASK_STATE: self.task_state
        }

    def update_state_json(self, json):
        """
        Update the state of the monitor. Used in repopulating the state from internal store.
        :param json:
        :return:
        """
        self.task_starttime = json[MonitorContext.TASK_TIMESTAMP]
        self.task_state = json[MonitorContext.TASK_STATE]
        
    def get_json(self):
        """
        Return a json object combining both state information and config information
        :return:
        """
        # Merge both config and state into one json.
        result = self.get_config_json()
        result.update(self.get_state_json())
        return result
