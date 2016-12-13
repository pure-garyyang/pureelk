#!/bin/bash

PUREELK_PATH=/var/lib/pureelk
PUREELK_CONF=$PUREELK_PATH/conf
PUREELK_ESDATA=$PUREELK_PATH/esdata
PUREELK_LOG=/var/log/pureelk

PUREELK_ES=pureelk-elasticsearch
PUREELK_KI=pureelk-kibana
PUREELK=pureelk

GREEN='\033[1;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

PUREELK_SCRIPT_URL=https://raw.githubusercontent.com/pureelk/pureelk/master/pureelk.sh
PUREELK_SCRIPT_LOCALPATH=$PUREELK_PATH/pureelk.sh

print_help() {
  echo "Usage: $0 {help|install|start|stop|attach|delete}"
}

print_info() {
  printf "${GREEN}$1${NC}\n"
}

print_warn() {
  printf "${YELLOW}$1${NC}\n"
}

detect_distro()
{
  # init process is pid 1
  INIT=`ls -l /proc/1/exe`
  if [[ $INIT == *"upstart"* ]]; then
    SYSTEMINITDAEMON=upstart
    config_upstart
  elif [[ $INIT == *"systemd"* ]]; then
    SYSTEMINITDAEMON=systemd
    config_systemd
  elif [[ $INIT == *"/sbin/init"* ]]; then
    INIT=`/sbin/init --version`
    if [[ $INIT == *"upstart"* ]]; then
      SYSTEMINITDAEMON=upstart
      config_upstart
    elif [[ $INIT == *"systemd"* ]]; then
      SYSTEMINITDAEMON=systemd
      config_systemd
    fi
  fi

  if [ -z "$SYSTEMINITDAEMON" ]; then
    echo "WARNING: Unknown distribution, defaulting to systemd - this may fail." >&2
    config_systemd
  fi
}

config_upstart() {
  curl -o ${PUREELK_SCRIPT_LOCALPATH} ${PUREELK_SCRIPT_URL}
  chmod u+x ${PUREELK_SCRIPT_LOCALPATH}

  cat > /etc/init/pureelk.conf << END_OF_UPSTART
  start on runlevel [2345]
  stop on [!2345]
  task
  exec ${PUREELK_SCRIPT_LOCALPATH} start
END_OF_UPSTART
}

config_systemd() {
  curl -o ${PUREELK_SCRIPT_LOCALPATH} ${PUREELK_SCRIPT_URL}
  chmod u+x ${PUREELK_SCRIPT_LOCALPATH}

  cat > /etc/systemd/system/docker-pureelk.service << END_OF_SYSTEMD

  [Unit]
  Description=pureelk container
  Requires=docker.service
  After=docker.service

  [Service]
  Type=oneshot
  ExecStart=${PUREELK_SCRIPT_LOCALPATH} start
  ExecStop=${PUREELK_SCRIPT_LOCALPATH} stop
  RemainAfterExit=yes

  [Install]
  WantedBy=default.target
END_OF_SYSTEMD

  systemctl enable docker-pureelk.service
}

install() {
  if [ "$(uname)" == "Linux" ]; then
      if [ $(dpkg-query -W -f='${Status}' docker-engine 2>/dev/null | grep -c "ok installed") -eq 0 ];
      then
          print_warn "Docker not yet installed, installing..."
          curl -sSL https://get.docker.com/ | sh
      else
          print_info "Docker is already installed"
      fi
  fi

  print_info "Pulling elasticsearch image..."
  docker pull elasticsearch:2

  print_info "Pulling kibana image..."
  docker pull kibana:4

  print_info "Pulling pureelk image..."
  docker pull pureelk/pureelk

  print_info "Creating local pureelk folders at $PUREELK_PATH"

  if [ ! -d "$PUREELK_CONF" ]; then
      sudo mkdir -p $PUREELK_CONF
  fi

  if [ ! -d "$PUREELK_ESDATA" ]; then
      sudo mkdir -p $PUREELK_ESDATA
  fi

  if [ ! -d "$PUREELK_LOG" ]; then
      sudo mkdir -p $PUREELK_LOG
  fi

  detect_distro

  print_info "Installation complete."
}

start_containers() {
  print_info "Starting PureElk elasticsearch container..."
  RUNNING="$(docker inspect -f '{{.State.Running}}' $PUREELK_ES)"
  if [ $? -eq 1 ];
  then
      print_warn "$PUREELK_ES doesn't exist, starting..."
      docker run -d -P --name=$PUREELK_ES --log-opt max-size=50m -v "$PUREELK_ESDATA":/usr/share/elasticsearch/data elasticsearch:2 -Des.network.host=0.0.0.0
  elif [ "$RUNNING" == "false" ];
  then
      docker start $PUREELK_ES
  else
      print_warn "$PUREELK_ES is already running."
  fi

  print_info "Start PureElk kibana container..."
  RUNNING="$(docker inspect -f '{{.State.Running}}' $PUREELK_KI)"
  if [ $? -eq 1 ];
  then
      print_warn "$PUREELK_KI doesn't, starting..."
      docker run -d -p 5601:5601 --name=$PUREELK_KI --log-opt max-size=50m --link $PUREELK_ES:elasticsearch kibana:4
  elif [ "$RUNNING" == "false" ];
  then
      docker start $PUREELK_KI
  else
      print_warn "$PUREELK_KI is already running."
  fi

  print_info "Start PureElk container..."
  RUNNING="$(docker inspect -f '{{.State.Running}}' $PUREELK)"
  if [ $? -eq 1 ];
  then
      print_warn "$PUREELK doesn't exist, starting..."
      docker run -d -p 8080:8080 --name=$PUREELK --log-opt max-size=50m -v "$PUREELK_CONF":/pureelk/worker/conf -v "$PUREELK_LOG":/var/log/pureelk --link $PUREELK_ES:elasticsearch pureelk/pureelk
  elif [ "$RUNNING" == "false" ];
  then
      docker start $PUREELK
  else
      print_warn "$PUREELK is already running."
  fi

  print_info "PureELK management endpoint is at http://localhost:8080"
  print_info "PureELK Kibana endpoint is at http://localhost:5601"
}

stop_containers() {
  print_info "Stopping PureELK container..."
  docker stop -t 2 $PUREELK

  print_info "Stopping PureELK Kibana container..."
  docker stop $PUREELK_KI

  print_info "Stopping PureELK elasticsearch container..."
  docker stop $PUREELK_ES
}

attach_pureelk() {
  print_info "Attaching to PureELK container..."
  docker exec -it $PUREELK bash
}

delete_containers() {
  print_info "Removing PureELK container..."
  docker rm -f $PUREELK

  print_info "Removing PureELK Kibana container..."
  docker rm -f $PUREELK_KI

  print_info "Removing PureElk elastic search container..."
  docker rm -f $PUREELK_ES
}

if [ -n "$1" ];
  then
    case $1 in
      help)
         print_help
         ;;
      install)
         install
         start_containers
         ;;
      start)
         start_containers
         ;;
      stop)
         stop_containers
         ;;
      attach)
         attach_pureelk
         ;;
      delete)
         delete_containers
         ;;
      *)
        print_help
        exit 1
    esac

    else
    print_help
fi
