#! /bin/bash

#set -x

# Default to build with TAG "test"
TAG="test"
if [ ! -z "$1" ]
  then
    TAG=$1
fi

docker build -t pureelk/pureelk:$TAG .
