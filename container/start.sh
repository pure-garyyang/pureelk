#! /bin/bash

set -x

#statements
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

# check for existing pureelk indices in the elasticsearch linked container
# if none exist populate the kibana index with pureelk index patterns and kibana dashboard
# user just needs to navigate to kibana and start monitoring

python ./getPureElkIndex.py

if [ $? -eq 1 ]
    then
        # no pureelk-global-arrays index found, run elasticdump to import new index patterns and kibana dashboards
        # so users has a one-button experience
        echo "Importing index patterns into elasticsearch..."
        /node_modules/elasticdump/bin/elasticdump --input=/pureelk/elasticdump_pureelk --output=http://elasticsearch:9200/.kibana
elif [ $? -eq 2 ]
    then
        # Stop the container by erroring out from the script.
        echo "Didn't detect elastic search cluster. Aborting..."
        exit 1
fi

# Start the Flask web-site
python web/app.py --array-configs=$CONF_DIR --logfile=/var/log/pureelk/rest.log &



