Monitoring a Pure Storage FlashArray with ELK
---------------------------------------------

1. [Overview](#overview)
2. [Getting Started](#getting-started)
  * [System Requirements](#system-requirements)
  * [Installation](#installation)
  * [Configuring PureELK](#configuring-pureelk)
  * [Start Monitoring a FlashArray](#start-monitoring-a-flasharray)
  * [Stop Monitoring a FlashArray](#stop-monitoring-a-flasharray)
  * [Accessing PureELK](#accessing-pureelk)
  * [Configuring Kibana for PureELK](#configuring-kibana-for-pureelk)
  * [Running PureELK](#running-pureelk)
  * [Data Persistence](#data-persistence)
  * [Automatic Start of PureELK](#automatic-start-of-pureelk)
3. [License](#license)

## Overview

PureELK is an open source monitoring solution for Pure Storage FlashArrays.

Why use PureELK? All Pure Storage FlashArrays send data about the array to Pure Storage every 30 seconds and this data is visible through the Pure1 dashboard. This rich SaaS platform allows you to view the health, performance, and capacity of the array from anywhere. There are some customers that can't take advantage of this feature due to high security demands. PureELK allows customers with security concerns to still have a rich platform to visualize array health and performance data. There are others that love data and visualization and PureELK provides customers with the ability to learn more about data on their FlashArray.

<img src="https://github.com/pureelk/pureelk/raw/master/doc/pureelk_network_architecture.png" height=200px width="50%">

PureELK utilizes the popular ELK stack (Elasticsearch, Logstash, and Kibana), a front end written in Nodejs to easily manage FlashArrays, and Pure Storage FlashArray REST APIs in the back end all configured and deployed using Docker containers.

<img src="https://github.com/pureelk/pureelk/raw/master/doc/pureelk_solution_stack.png" height=250px width="50%">

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

Once installation is completed, the containers will be started and PureELK will be accessible at: http://VM-HOSTNAME:8080.

NOTE: The docker daemon runs as the root user and binds to a Unix socket instead of a TCP port. By default, that Unix socket is owned by root. To run Docker commands without ``` sudo ``` it's necessary to add the appropriate username to the Docker group (created during install). To perform this task, enter the following command on the Docker VM: ``` sudo usermod -aG docker <username> ```. For this to take effect, you will need to log out and back into the shell.

### Configuring PureELK


### Start Monitoring a FlashArray

Before configuring PureELK, the API key is needed for the username that will be pulling data from the FlashArray to PureELK.

To get the API key, access the Pure Storage FlashArray GUI and navigate to the Users section under the System menu.

Mouse over the user's name and select the cogwheel next to the name and select Show API Token.

Navigate to PureELK configuration page at http://VM-HOSTNAME:8080 and click the orange + to add FlashArray(s).

* Enter the FlashArray hostname or IP
* Enter the username
* Enter the API key
* [Optional] Set Metric TTL (default: 90 days)
* [Optional] Set the collect interval (default: 60 seconds)
* Click Start monitoring

The PureELK screen will display if connecting to the FlashArray was a success or failure.

#### Stop Monitoring a FlashArray

Navigate to PureELK configuration page at http://VM-HOSTNAME:8080 and click the trash can icon next to the name of the FlashArray that is being monitored.

### Accessing PureELK

Access Kibana directly by navigating to http://VM-HOSTNAME:5061 or PureELK at http://VM-HOSTNAME:8080 and click Go to Kibana.

### Configuring Kibana for PureELK

Kibana is a very robust platform that allows an incredible amount of customization to view data that is stored in logstash.

To simplify getting started with Kibana, numerous dashboards, searches, and visualizations have been preloaded. This may satisfy the needs of most but if additional views are required, see the Kibana user guide for creating custom queries.

### Running PureELK

During installation, PureELK is automatically started and will continue to run until manually stopped or the host is shutdown. A PureELK upstart init script has been included to start and stop the applications.

To further operate PureELK, command line options are available on the host VM.

```
Usage: /var/lib/pureelk/pureelk.sh {help|install|start|stop|attach|delete}
```

##### help

Shows the help options menu.

##### install

Deploys PureELK in Docker containers on the local host. Automatically performed during initial deployment but can be run again if ``` delete ``` action is performed.

##### start

PureELK is automatically started after deployment and during host boot. ``` Start ``` will start all three containers if not already running.

#### stop

Stops the PureELK containers.

##### attach

Connect to the PureELK docker container in a bash prompt.

##### delete

Force stop of PureELK and deletes the container from the host. *Does not delete the Docker images*.

```
$ bash /var/lib/pureelk/pureelk.sh delete
Removing PureElk container...
pureelk
Removing PureElk Kibana container...
pureelk-kibana
Removing PureElk elastic search container...
pureelk-elasticsearch
```

### Data Persistence

Data persistence is handled by using a host directory mounted as a data volume.

* Elasticsearch data is stored in ``` /usr/share/elasticsearch/data ```
* PureELK: ``` /var/lib/pureelk/ ``` and ```/var/log/pureelk ```

### Automatic Start of PureELK

To facilitate the automatic start of PureELK, an upstart script, ``` pureelk.conf ``` has been added to ``` /etc/init/ ```. Given the dependency on Upstart, the recommended Linux distribution and version is Ubuntu 14.04 LTS.

## License
PureELK is Open Source software released under the Apache 2.0 License.
