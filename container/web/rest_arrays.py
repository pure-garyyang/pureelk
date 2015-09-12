
import flask
import purestorage

from flask import current_app
from pureelk.store import Store
from rest_api import rest_api, make_rest_response, make_error
from pureelk.arraycontext import ArrayContext
from errorcodes import ErrorCodes


ARRAY_CONFIGS = "array-configs"
USERNAME = "username"
PASSWORD = "password"
HOST = "host"

arrays = flask.Blueprint('arrays', __name__)


@arrays.route("/", methods=["GET"])
@rest_api
def get_arrays():
    """
    Gets all the arrays
    :return: List of arrays in the system
    """
    store = Store(array_config_path(), current_app.logger)
    array_dict = store.load_arrays()
    return [a.get_json() for a in array_dict.values()]


@arrays.route("/", methods=["POST"])
@rest_api
def add_array(json_body=None):
    """
    Add an array to the system. The array is specified in the body.
    :return:
    The array object added, which contains the array_id which could be used later
    to delete this array.
    """
    error_data = validate_array_input(json_body)
    if error_data:
        return make_rest_response(error_data, 400)

    try:
        apitoken, array_id, array_name, purity_version = get_array_info(json_body[HOST], json_body[USERNAME], json_body[PASSWORD])
    except Exception as e:
        return make_rest_response(
            make_error(ErrorCodes.ArrayError.value, "Error encountered when connecting to the array: {}".format(e)),
            400)

    del json_body[PASSWORD]
    json_body.update({
        ArrayContext.API_TOKEN: apitoken,
        ArrayContext.NAME: array_name,
        ArrayContext.ID: array_id,
        ArrayContext.PURITY_VERSION: purity_version
    })

    store = Store(array_config_path(), current_app.logger)

    existing_arrays = store.load_arrays()

    if array_id in existing_arrays:
        return make_rest_response(
            make_error(
                ErrorCodes.ArrayAlreadyExists.value,
                "Array of the same id already exists with the name '{}'.".format(
                    existing_arrays[array_id].name)),
            409)

    array = ArrayContext()
    array.update_config_json(json_body)
    store.save_array_config(array)

    # Return the array object created.
    return array.get_json()

@arrays.route("/<array_id>", methods=["PUT"])
@rest_api
def update_array(array_id, json_body=None):
    """
    Update an array in the system. The properties specified in the body will be merged into the array
    :param array_id: The array id.
    :param json_body: The properties to be updated.
    :return: The full array object.
    """
    # We don't allow changing the array id in put.
    if ArrayContext.ID in json_body:
        del json_body[ArrayContext.ID]

    store = Store(array_config_path(), current_app.logger)
    array_dict = store.load_arrays()

    if array_id not in array_dict:
        return make_rest_response(
            make_error(ErrorCodes.ArrayNotFound.value, "Array not found with id {}".format(array_id)),
            404)

    array = array_dict[array_id]

    # The user is trying to update the array token/name by passing in username/password?
    if USERNAME in json_body and PASSWORD in json_body:
        try:
            apitoken, array_id, array_name, purity_version = get_array_info(
                json_body[HOST] if HOST in json_body else array.host,
                json_body[USERNAME],
                json_body[PASSWORD])
        except Exception as e:
            return make_rest_response(
                make_error(ErrorCodes.ArrayError.value, "Error encountered when connecting to the array: {}".format(e)),
                400)

        # The id retrieved from array doesn't match with the original anymore!!
        if array_id != array.id:
            return make_rest_response(
                make_error(ErrorCodes.ArrayIdMismatch.value,
                           "Array id mismatch. Original id = {}, new id fetched from array = {}".format(array.id, array_id)),
                400)

        del json_body[PASSWORD]
        json_body.update({
            ArrayContext.API_TOKEN: apitoken,
            ArrayContext.NAME:  array_name,
            ArrayContext.PURITY_VERSION: purity_version
        })

    array.update_config_json(json_body)
    store.save_array_config(array)
    return array.get_json()


@arrays.route("/<array_id>", methods=["DELETE"])
def delete_array(array_id):
    """
    Delete an array
    :param array_id:
    :return:
    """
    store = Store(array_config_path(), current_app.logger)

    arrays = store.load_arrays()

    array_deleted = None
    if array_id in arrays:
        array_deleted = arrays[array_id]
        store.remove_array_config(array_id)

    return make_rest_response(
        array_deleted.get_json() if array_deleted else None,
        200)

@arrays.route("/test", methods=["POST"])
def test_array():
    """
    Test if an array config is legit.
    :return: true/false
    """
    pass


def validate_array_input(input_json):
    if "host" not in input_json:
        return make_error(ErrorCodes.RequireFieldMissing.value, "'host' is not specified.")

    if "username" not in input_json:
        return make_error(ErrorCodes.RequireFieldMissing.value, "'username' is not specified.")

    if "password" not in input_json:
        return make_error(ErrorCodes.RequireFieldMissing.value, "'password' is not specified.")

    return None


def array_config_path():
    return current_app.config[ARRAY_CONFIGS]


def get_array_info(host, username, password):
    ps_client = purestorage.FlashArray(host, username, password)
    array_obj = ps_client.get()
    return ps_client._api_token, array_obj["id"], array_obj["array_name"], array_obj["version"]
