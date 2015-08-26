#! /bin/bash

service rabbitmq-server stop

# stop all processes that are under pureelk folder
ps aux | grep pureelk | grep -v 'grep' | tr -s ' ' | cut -d ' ' -f 2 | xargs kill -9
