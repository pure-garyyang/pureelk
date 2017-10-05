from __future__ import absolute_import

import time

import purestorage
from elasticsearch import Elasticsearch
from .worker import app
from .worker import logger
from .worker import context
from .purecollector import PureCollector

SCHEDULE_TOLERANCE = 5
TASK_TIMEOUT = 300

@app.task
def arrays_schedule():
    """
    Main schedule task to kick of data collections for all arrays
    :return:
    """
    # Prepare the context based on latest configs
    context.prepare()
    now = time.time()

    for array_name, array_context in context.array_contexts.iteritems():

        last_task_completed = array_context.is_task_completed

        # If the next run's time stamp is within 5 second of now, we'll just run it now,
        # instead of waiting for the next schedule.
        is_time_to_run = array_context.task_starttime + array_context.frequency <= now + SCHEDULE_TOLERANCE

        if array_context.enabled and last_task_completed and is_time_to_run:
            task = array_collect.apply_async([array_context], expires=TASK_TIMEOUT)
            array_context.task = task
            array_context.task_starttime = now
            logger.info("Scheduled collection for array {} at host {}".format(array_name, array_context.host))
        else:
            logger.info("Skip array {}. Enabled = {}, Last task completed = {}, Time to run now = {}".format(
                array_name, array_context.enabled, last_task_completed, is_time_to_run))


@app.task
def array_collect(array_context):
    logger.info("Collecting info for array '{}'".format(array_context.name))

    # Create PureStorage client and Elasticsearch client
    ps_client = purestorage.FlashArray(array_context.host, api_token=array_context.api_token, rest_version="1.4")
    # "elasticsearch" is the internal link to PureELK ES server
    es_client = Elasticsearch(hosts="elasticsearch:9200", retry_on_timeout=True)

    pure_collector = PureCollector(ps_client, es_client, array_context)
    pure_collector.collect()

