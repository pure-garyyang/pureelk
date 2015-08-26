#! /bin/bash

# This is the startup script for the container. See Dockerfile instructions.

# Start the rabbitmq which is used by the Celery worker
service rabbitmq-server start

# We are running Celery worker as root in the container. We must set this env variable for
# Celery to start
export C_FORCE_ROOT=1

CONF_DIR=/pureelk/worker/conf

# Start the celery scheduling worker. It sends the actual task out.
celery -A pureelk.worker worker --loglevel=info --beat --config workerconfig --workdir worker/ --logfile /var/log/pureelk/scheduler.log --array-configs $CONF_DIR -c 1 &

# Start the array collection tasks on array_tasks queue, using gevent concurrency mode since it is I/O intensive
celery -A pureelk.worker worker --loglevel=info --config workerconfig --workdir worker/ --logfile /var/log/pureelk/array-tasks.log -P gevent -Q array_tasks  &

# Export the python modules from worker and web folder
export PYTHONPATH=$PYTHONPATH:/pureelk/web/:/pureelk/worker/

# Start the Flask web-site
python web/app.py --array-configs=$CONF_DIR --logfile=/var/log/pureelk/rest.log &



