from __future__ import absolute_import

from celery import Celery
from celery import signals
from celery.bin import Option
from celery.utils.log import get_task_logger

from .context import Context


'''
    Celery worker setup
'''

ARRAY_CONFIGS = "array_configs"

# logger for the worker tasks.
logger = get_task_logger(__name__)

# global execution context
context = None

app = Celery('pureelk.worker',
             include=['pureelk.tasks'])

app.user_options['preload'].add(Option(
    "-a", '--array-configs', default='',
    help='Path to array configs',
))

@signals.user_preload_options.connect
def handle_preload_options(options, **kwargs):
    global context
    context = Context(options[ARRAY_CONFIGS])





