 
import flask

from flask import current_app
from pureelk.store import Store
from rest_api import rest_api, make_rest_response, make_error
from pureelk.monitorcontext import MonitorContext
from errorcodes import ErrorCodes
import uuid


# HACK because we are using the same directory to store
# monitors and arrays for now , I should generalize
# later into asingle CONFIG_DIR instead of being named by 
# array or monitor
MONITOR_CONFIGS = "array-configs"

monitors = flask.Blueprint('monitors', __name__)


@monitors.route("/", methods=["GET"])
@rest_api
def get_monitors():
    """
    Gets all the monitors
    :return: List of monitors in the system
    """
    store = Store(monitor_config_path(), current_app.logger)
    monitor_dict = store.load_monitors()
    return [m.get_json() for m in monitor_dict.values()]


@monitors.route("/", methods=["POST"])
@rest_api
def add_monitor(json_body=None):
    """
    Add a monitor to the system. 
    :return:
    The monitor object added, which contains the monitor_id which could be used later
    to delete this monitor.
    """
    error_data = validate_monitor_input(json_body)
    if error_data:
        return make_rest_response(error_data, 400)

    # create a new UUID for the monitor and store it as an id
    monitor_id = str(uuid.uuid4())

    json_body.update({
        MonitorContext.ID: monitor_id,
    })

    store = Store(monitor_config_path(), current_app.logger)

    existing_monitors = store.load_monitors()

    if monitor_id in existing_monitors:
        return make_rest_response(
            make_error(
                ErrorCodes.MonitorAlreadyExists.value,
                "monitor of the same id already exists"),
            409)

    monitor = MonitorContext()
    monitor.update_config_json(json_body)
    store.save_monitor_config(monitor)

    # Return the monitor object created.
    return monitor.get_json()

@monitors.route("/<monitor_id>", methods=["PUT"])
@rest_api
def update_monitor(monitor_id, json_body=None):
    """
    Update an monitor in the system. The properties specified in the body will be merged into the monitor
    :param monitor_id: The monitor id.
    :param json_body: The properties to be updated.
    :return: The full monitor object.
    """
    # We don't allow changing the monitor id from the client.
    if MonitorContext.ID in json_body:
        del json_body[MonitorContext.ID]

    store = Store(monitor_config_path(), current_app.logger)
    monitor_dict = store.load_monitors()

    if monitor_id not in monitor_dict:
        return make_rest_response(
            make_error(ErrorCodes.MonitorNotFound.value, "Monitor not found with id {}".format(monitor_id)),
            404)

    # get existing data from monitor dict
    monitor = monitor_dict[monitor_id]

    # remove its on-disk config 
    store.remove_monitor_config(monitor.id)

    # now update internal state of monitor with client-side json data
    monitor.update_config_json(json_body)

    # since I am changing some thing about the monitor generate a new UUID so
    # the algorithm to limit duplicate message triggering works correctly 
    # in purecollector.py monitor()
    monitor.id = str(uuid.uuid4())

    # now save the json state to disk
    store.save_monitor_config(monitor)

    return monitor.get_json()


@monitors.route("/<monitor_id>", methods=["DELETE"])
def delete_monitor(monitor_id):
    """
    Delete an monitor
    :param monitor_id:
    :return:
    """
    store = Store(monitor_config_path(), current_app.logger)

    monitors = store.load_monitors()

    monitor_deleted = None
    if monitor_id in monitors:
        monitor_deleted = monitors[monitor_id]
        store.remove_monitor_config(monitor_id)

    return make_rest_response(
        monitor_deleted.get_json() if monitor_deleted else None,
        200)


def validate_monitor_input(input_json):

    if "type" not in input_json:
        return make_error(ErrorCodes.RequireFieldMissing.value, "'type' is not specified.")

    if "array_name" not in input_json:
        return make_error(ErrorCodes.RequireFieldMissing.value, "'array_name' is not specified.")

    if "vol_name" not in input_json:
        return make_error(ErrorCodes.RequireFieldMissing.value, "'vol_name' is not specified.")

    if "compare" not in input_json:
        return make_error(ErrorCodes.RequireFieldMissing.value, "'compare' is not specified.")

    if "metric" not in input_json:
        return make_error(ErrorCodes.RequireFieldMissing.value, "'metric' is not specified.")

    if "value" not in input_json:
        return make_error(ErrorCodes.RequireFieldMissing.value, "'value' is not specified.")

    if "hits" not in input_json:
        return make_error(ErrorCodes.RequireFieldMissing.value, "'hits' is not specified.")

    if "window" not in input_json:
        return make_error(ErrorCodes.RequireFieldMissing.value, "'window' is not specified.")

    return None


def monitor_config_path():
    return current_app.config[MONITOR_CONFIGS]

