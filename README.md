<!--
http://www.apache.org/licenses/LICENSE-2.0.txt


Copyright 2015 Pure Storage

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
-->

# Monitoring Pure Storage Flash Array with ELK

1. [Overview](#overview)
2. [Getting Started](#getting-started)
  * [System Requirements](#system-requirements)
  * [Installation](#installation)
  * [Configuring PureELK](#configuring-pureelk)
  ** Start Monitoring a FlashArray
  ** Stop Monitoring a FlashArray
  * [Accessing PureELK](#accessing-pureelk)
  * [Configuring Kibana for PureELK](#configuring-kibana)
  * [Running PureELK](#running-pureelk)
  ** Automatic Start of PureELK
3. [Contributing](#contributing)
4. [TODO](#todo)
5. [Contributors](#contributors)
  * [Initial Authors](#initial-authors)
  * [Maintainers](#maintainers)
6. [License](#license)

## Overview

PureELK is an open source monitoring solution for Pure Storage FlashArrays.

Why use PureELK? All Pure Storage FlashArrays send data about the array to Pure Storage every 30 seconds and this data is visible through the Pure1 dashboard. This rich SaaS platform allows you to view the health, performance, and capacity of the array from anywhere. There are some customers that can't take advantage of this feature due to high security demands. PureELK allows customers with security concerns to still have a rich platform to visualize array health and performance data. There are others that love data and visualization and PureELK provides customers with the ability to learn more about data on their FlashArray.

PureELK utilizes the popular ELK stack (Elasticsearch, Logstash, and Kibana), a front end written in Nodejs to easily manage FlashArrays, and Pure Storage FlashArray REST APIs in the back end all configured and deployed using Docker containers.

## Getting Started

### System Requirements

* Ubuntu 14.04 LTS installed (dependency on Ubuntu for upstart)
* 4 GB RAM allocated
* 20 GB capacity to store 90 days of historical data for each FlashArray

### Installation

To install PureELK, run the following command on the host VM:

```
$ curl -s https://raw.githubusercontent.com/pureelk/pureelk/master/pureelk.sh | sudo bash -s install
```
The installation script will install the latest version of Docker then pull the following container images from Docker Hub:

* Elasticsearch
* Kibana
* PureELK

Once installation is completed, the containers will be started and PureELK will be accessible at: http://HOSTNAME:8080.

### Configuring PureELK

#### Start Monitoring a FlashArray

Before configuring PureELK, the API key is needed for the username that will be pulling data from the FlashArray to PureELK.

To get the API key, access the Pure Storage FlashArray GUI and navigate to the Users section under the System menu.

Mouse over the user's name and select the cogwheel next to the name and select Get API Key <-- NEED TO VERIFY THIS STEP.

Navigate to PureELK configuration page at http://VM-HOSTNAME:8080 and click the orange + to add FlashArray(s).

* Enter the FlashArray hostname or IP
* Enter the username
* Enter the API key
* Set Metric TTL (default: 90 days)
* Set the collect interval (default: 60 seconds)
* Click Start monitoring

The PureELK screen will display if connecting to the FlashArray was a success or failure.

#### Stop Monitoring a FlashArray

Navigate to PureELK configuration page at http://VM-HOSTNAME:8080 and click the trash can icon next to the name of the FlashArray that is being monitored.

### Accessing PureELK Monitoring

Access Kibana directly by navigating to http://VM-HOSTNAME:5061 or PureELK at http://VM-HOSTNAME:8080 and click Go to Kibana

### Configuring Kibana for PureELK

Kibana is a very robust platform that allows an incredible amount of customization to view data that is stored in logstash.

To simplify getting started with Kibana, a few bootstrap queries and dashboards have been preloaded. This may satisfy the needs of most but if additional views are required, see the Kibana user guide for creating customer queries.

List of dashboards, queries, etc

### Running PureELK

During installation, PureELK is automatically started and will continue to run until manually stopped or the host is shutdown. A PureELK upstart init script has been included to start and stop the applications.

To further operate PureELK, command line options are available on the host VM.

``` Usage: /var/lib/pureelk/pureelk.sh {help|install|start|stop|attach|delete}
```

##### help

Shows this help options menu.

##### install

Deploys PureELK in Docker containers on the local host. Automatically performed during initial deployment but can be run again if ``` delete ``` action is performed.

##### start

PureELK is automatically started after deployment and during host boot. ``` Start ``` will start all three containers if not already running.

#### stop

Stops the PureELK containers.

##### attach

Connect to the PureELK docker container in a bash prompt.

##### delete

Force stop of PureELK and deletes the container from the host. Does not delete the Docker images.

```
$ bash /var/lib/pureelk/pureelk.sh delete
Removing PureElk container...
pureelk
Removing PureElk Kibana container...
pureelk-kibana
Removing PureElk elastic search container...
pureelk-elasticsearch
```

#### Automatic Start of PureELK

To facilitate the automatic start of PureELK, an upstart script, ``` pureelk.conf ``` has been added to ``` /etc/init/ ```. Given the dependency on Upstart, the recommended Linux distribution and version is Ubuntu 14.04 LTS.

## TODO

* Detect init system and add appropriate script to enable the automatic start of containers.
* Modify deployment of PureELK to use docker-compose or docker-swarm. Using native clustering may negate need for init script.

## License
PureELK is Open Source software released under the Apache 2.0 [License](LICENSE).
