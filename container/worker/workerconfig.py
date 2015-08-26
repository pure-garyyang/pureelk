from datetime import timedelta

# Use the default rabbits MQ on the container
BROKER_URL="amqp://guest:guest@127.0.0.1:5672//"
CELERY_RESULT_BACKEND="amqp://guest:guest@127.0.0.1:5672//"

CELERYBEAT_SCHEDULE = {
    'arrays_schedule': {
        'task': 'pureelk.tasks.arrays_schedule',
        'schedule': timedelta(seconds=10)
    }
}

CELERY_TIMEZONE = 'UTC'

# Send the following tasks to different queues such that
# they will be pick up by a different worker.
CELERY_ROUTES = {
    'pureelk.tasks.array_collect': {'queue': 'array_tasks'}
}
