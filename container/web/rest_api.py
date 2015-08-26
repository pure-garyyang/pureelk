import flask
from flask import request, make_response, current_app
from errorcodes import ErrorCodes
import json

from functools import wraps


def rest_api(f):
    """
    A decorator for rest API
    :param f:
    :return:
    """
    @wraps(f)
    def decorator(*args, **kwargs):

        json_object = None
        if request.data:
            try:
                json_object = json.loads(request.data)
            except ValueError as v:
                current_app.logger.info("Invalid input = {}, error = {}".format(request.data, v))
                return make_rest_response(make_error(ErrorCodes.InvalidInput.value, "Input is invalid"), 400)

        if json_object:
            result = f(*args, **dict(kwargs, json_body=json_object))
        else:
            result = f(*args, **kwargs)

        if isinstance(result, flask.Response):
            return result
        else:
            return flask.Response(json.dumps(result), content_type='application/json; charset=utf-8')

    return decorator


def make_rest_response(error, status_code):
    response = make_response(json.dumps(error), status_code)
    response.headers["Content-Type"] = "'application/json; charset=utf-8'"
    return response

def make_error(code, message):
    return {
        "code": code,
        "message": message
    }
