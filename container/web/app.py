import argparse
import rest_arrays
import sys
import os

import logging
from logging import Formatter
from logging.handlers import RotatingFileHandler

from flask import Flask, send_from_directory
from gevent.wsgi import WSGIServer

app = Flask(__name__)

# Registering blueprints
app.register_blueprint(rest_arrays.arrays, url_prefix='/rest/arrays')

# As initialized upon program startup, the first item of this list (sys.path), path[0],
# is the directory containing the script that was used to invoke the Python interpreter.
# This app may not always be started from the script's folder. We need to use the base_dir
# when loading static content from a relative path.
app.base_dir = sys.path[0]

app.static_folder = os.path.join(app.base_dir, 'static')

@app.route('/')
def index():
    return send_from_directory(app.static_folder, "index.html")

@app.route('/css/<path:filename>')
def css(filename):
    return send_from_directory(os.path.join(app.static_folder, 'css'), filename)

@app.route('/fonts/<path:filename>')
def fonts(filename):
    return send_from_directory(os.path.join(app.static_folder, 'fonts'), filename)

@app.route('/js/<path:filename>')
def js(filename):
    return send_from_directory(os.path.join(app.static_folder, 'js'), filename)

@app.route('/img/<path:filename>')
def img(filename):
    return send_from_directory(os.path.join(app.static_folder, 'img'), filename)

@app.route('/webapp/<path:filename>')
def webapp(filename):
    return send_from_directory(os.path.join(app.static_folder, 'webapp'), filename)

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Runs the pureelk web server.')

    parser.add_argument('-a', '--array-configs', dest="array_configs", required=True,
                        help="Path to the folder containing the array config files.")
    parser.add_argument('-p', '--port', type=int, default=8080, dest='port')
    parser.add_argument('-l', '--logfile', dest='logfile')

    args = parser.parse_args()

    handler = RotatingFileHandler(args.logfile, maxBytes=20*1024*1024, backupCount=1)
    handler.setLevel(logging.INFO)
    handler.setFormatter(Formatter("%(asctime)s [%(levelname)s] %(message)s"))

    app.logger.addHandler(handler)
    app.logger.setLevel(logging.INFO)

    if not os.path.exists(args.array_configs):
        raise ValueError("Array config path doesn't exists: '{}'".format(args.array_configs))

    app.config["array-configs"] = args.array_configs

    http_server = WSGIServer(('', args.port), app)
    http_server.serve_forever()
