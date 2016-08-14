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
  * [Running PureELK](#running-pureelk)
3. [Contributing](#contributing)
  * [Author a Plugin](#author-a-plugin)
4. [License](#license)
5. [Contributors](#contributors)
  * [Initial Authors](#initial-authors)
  * [Maintainers](#maintainers)

## Overview

PureELK is an open source monitoring solution for Pure Storage FlashArrays.

Why use PureELK? All Pure Storage FlashArrays send data about the array to Pure Storage every 30 seconds and this data is visible through the Pure1 dashboard. This rich SaaS platform allows you to view the health, performance, and capacity of the array from anywhere. There are some customers that can't take advantage of this feature due to high security demands. PureELK allows customers with security concerns to still have a rich platform to visualize array health and performance data. There are others that love data and visualization and PureELK provides customers with the ability to learn more about data on their FlashArray.

PureELK utilizes the popular ELK stack (Elasticsearch, Logstash, and Kibana) and Pure Storage FlashArray REST APIs all configured and deployed using Docker containers.

## Getting Started

### System Requirements

* Clean installation of Ubuntu 14.04 LTS
* 4 GB RAM
* 20 GB capacity to store 90 days of historical data for each FlashArray

### Installation

To install PureELK, run the following command:

```
$ curl -s https://raw.githubusercontent.com/pureelk/pureelk/master/pureelk.sh | sudo bash -s install

```
The installation script will install the latest version of Docker then pull the following container images from Docker Hub:

* Elasticsearch
* Kibana
* PureELK

Once installation is completed, the containers will be started and PureELK will be accessible at: http://HOSTNAME:8080.

### Configuring PureELK

### Running PureELK

During installation, PureELK is automatically started and will continue to run until manually stopped or the host is shutdown. A PureELK upstart init script has been included to start and stop the applications.

Additionally, PureELK has the following commands available:

* [Help](#help)
* [Install](#install)
* [Start](#start)
* [Stop](#stop)
* [Attach](#attach)
* [Delete](#delete)

#### Help

Shows this help options menu

``` Usage: /var/lib/pureelk/pureelk.sh {help|install|start|stop|attach|delete} ```

## License
PureELK is Open Source software released under the Apache 2.0 [License](LICENSE).
