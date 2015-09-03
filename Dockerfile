FROM ubuntu:14.04
MAINTAINER Gary Yang <garyyang@purestorage.com>; Cary Li <cary.li@purestorage.com>

# Expose a web endpoint for the management website
EXPOSE 8080

RUN apt-get update && apt-get install -y rabbitmq-server python-pip python-dev vim nodejs npm
RUN pip install Celery
RUN pip install purestorage
RUN pip install gevent
RUN pip install Flask
RUN pip install elasticsearch
RUN pip install python-dateutil
RUN pip install enum34

ENV target_folder /pureelk
ADD container/ $target_folder
WORKDIR $target_folder

RUN chmod +x start.sh
RUN mkdir -p /var/log/pureelk

# Run the startup script. Also run a long running process to prevent docker from existing. 
CMD ./start.sh && exec tail -f /etc/hosts

