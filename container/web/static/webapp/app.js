var pureelkApp = angular.module('pureelk', ['ngRoute', 'ngResource'])
    .config(function ($routeProvider, $resourceProvider) {
                $routeProvider
                    .when('/flasharrays',
                    {
                        controller: 'FlashArraysController',
                        templateUrl: '/webapp/partials/flasharrays.html'
                    })
                    .otherwise({redirectTo: '/flasharrays'});

                // Stop AngularJS from removing the slash at the end of URL. pureelk REST server
                // needs the /
                $resourceProvider.defaults.stripTrailingSlashes = false;
            })
    .factory('PureElkRestService', function ($resource) {
                 return $resource({}, {}, {
                     getArrays: {
                         method: 'GET',
                         url: 'rest/arrays/',
                         isArray: true
                     },
                     deleteArray: {
                         method: 'DELETE',
                         url: 'rest/arrays/:arrayid'
                     },
                     addArray: {
                         method: 'POST',
                         url: 'rest/arrays/',
                         headers: {'Content-Type': 'application/json'}
                     },
                     updateArray: {
                         method: 'PUT',
                         url: 'rest/arrays/:arrayid',
                         headers: {'Content-Type': 'application/json'}
                     },
                     changeArrayCollectionStatus: {
                         method: 'PUT',
                         url: 'rest/arrays/:arrayid'
                     },
                     getMonitors: {
                         method: 'GET',
                         url: 'rest/monitors/',
                         isArray: true
                     },
                     deleteMonitor: {
                         method: 'DELETE',
                         url: 'rest/monitors/:monitorid'
                     },
                     addMonitor: {
                         method: 'POST',
                         url: 'rest/monitors/',
                         headers: {'Content-Type': 'application/json'}
                     },
                     updateMonitor: {
                         method: 'PUT',
                         url: 'rest/monitors/:monitorid',
                         headers: {'Content-Type': 'application/json'}
                     },
                     changeMonitorCollectionStatus: {
                         method: 'PUT',
                         url: 'rest/monitors/:monitorid'
                     }
                 });
             })
    .controller('FlashArraysController',
                function ($scope, $log, $location, $window, $interval, PureElkRestService) {
                    $log.info('in FlashArrayController')

                    // initialize momentjs
                    moment().format();

                    $scope.deleteArray = function (array_id) {
                        PureElkRestService.deleteArray({arrayid: array_id});
                        $scope.reloadArray();
                    };

                    $scope.isCollecting = function(array) {
                        return array.hasOwnProperty('enabled') ? array.enabled : true;
                    }

                    $scope.getCollectionStatus = function(array) {
                        if (!array.task_state)
                            return "NOT STARTED";
                        if (!$scope.isCollecting(array))
                            return "PAUSED";
                        return array.task_state;
                    }

                    $scope.changeArrayCollectionStatus = function (array) {
                        // array context has "enabled=true" by default if "enabled" property doesn't exist
                        isEnabled = $scope.isCollecting(array);

                        // change collection status to opposite
                        array.enabled = !isEnabled;
                        PureElkRestService.changeArrayCollectionStatus({arrayid:array.id}, {enabled : array.enabled});
                        $log.info("Changed array collection status to " + array.enabled);
                    }


                    $scope.resetNewArray = function() {
                        $scope.newarray = { data_ttl : "90", frequency: "60" };
                        $scope.newarrayError = {};
                    }

                    $scope.setupArrayAdd = function() {
                        $scope.resetNewArray();
                    }

                    $scope.addArray = function () {
                        $log.info('Adding array: ' + $scope.newarray.host);

                        // make a quick clone of the new array object and modify the TTL to add 'days'
                        var cloneOfNewArray = JSON.parse(JSON.stringify($scope.newarray));
                        cloneOfNewArray.data_ttl = cloneOfNewArray.data_ttl + 'd';

                        PureElkRestService.addArray(angular.toJson(cloneOfNewArray)).$promise.then(function(data){
                            // success handler
                            $('#modalNewArray').modal('hide');
                            $scope.reloadArray();
                        }, function(error) {
                            if (error.data.message.indexOf("Invalid argument") > -1) {
                                $scope.newarrayError.message = "Unreachable FlashArray hostname, please try again."
                            } else if (error.data.message.indexOf("invalid credentials") > -1) {
                                $scope.newarrayError.message = "Invalid credentials, please try again."
                            } else {
                                $scope.newarrayError.message = error.data.message;
                            }
                        });
                    }

                    $scope.reloadArray = function () {
                        PureElkRestService.getArrays().$promise.then(function(arrayData) {
                           $scope.flasharrays = arrayData;
                        });
                    }

                    $scope.reloadArray();
                    $interval($scope.reloadArray, 5000);

                    // every second go in there to update the flasharray updated time (seconds ago)
                    $interval(function(){
                        for (var flasharray in $scope.flasharrays) {
                            flasharray.refresh_seconds_ago = Math.floor(new Date().getTime() / 1000 - flasharray.task_timestamp)
                        }
                    }, 1000)

                    $scope.getUpdatedAgo = function (epoch) {
                        if (!epoch)
                            return "-";

                        return moment.unix(epoch).fromNow();
                    }

                    $scope.kibanaURL =
                        $location.protocol() + "://" + $location.host() + ":5601/";

                    $scope.setupArrayEdit = function(flasharray) {

                        // set up a copy of the array to bind into the "edit array" view.
                        var editarray = $.extend(true, {}, flasharray);

                        // The backend doesn't persist password. We just set the array id there as a fake password
                        editarray.password = flasharray.id;
                        if (!!flasharray.data_ttl)
                        {
                            // Need to trim away the day unit string "d".
                            editarray.data_ttl = flasharray.data_ttl.substring(0, flasharray.data_ttl.length - 1);
                        }

                        $scope.arrayEdit = {
                            original: flasharray,
                            edit: editarray
                        };

                        $scope.editarrayError = {};
                    }

                    $scope.updateArray = function() {
                        $log.info('Updating array: ' + $scope.arrayEdit.original.id);
                        var original = $scope.arrayEdit.original;
                        var edit = JSON.parse(JSON.stringify($scope.arrayEdit.edit));

                        edit.data_ttl = edit.data_ttl + 'd';

                        // If username or password didn't change, we skip them so that server will not refresh the api token.
                        // Note that we use id to fake the password when setting up the edit dialog.
                        if (edit.username == original.username && edit.password == original.id)
                        {
                            delete edit.username;
                            delete edit.password;
                        }

                        PureElkRestService.updateArray({arrayid: edit.id}, angular.toJson(edit))
                            .$promise.then(function(data){
                                // success handler
                                $('#modalEditArray').modal('hide');
                                $scope.reloadArray();
                            }, function(error) {
                                $scope.editarrayError.message = error.data.message;
                            });
                    }
                    $scope.deleteMonitor = function (monitor_id) {
                        PureElkRestService.deleteMonitor({monitorid: monitor_id});
                        $scope.reloadMonitor();
                    };

                    $scope.isMonitorCollecting = function(monitor) {
                        return monitor.hasOwnProperty('enabled') ? monitor.enabled : true;
                    }

                    $scope.getMonitorCollectionStatus = function(monitor) {
                        if (!monitor.task_state)
                            return "NOT STARTED";
                        if (!$scope.isCollecting(monitor))
                            return "PAUSED";
                        return monitor.task_state;
                    }

                    $scope.changeMonitorCollectionStatus = function (monitor) {
                        // monitor context has "enabled=true" by default if "enabled" property doesn't exist
                        isEnabled = $scope.isMonitorCollecting(monitor);

                        // change collection status to opposite
                        monitor.enabled = !isEnabled;
                        PureElkRestService.changeMonitorCollectionStatus({monitorid:monitor.id}, {enabled : monitor.enabled});
                        $log.info("Changed monitor collection status to " + monitor.enabled);
                    }

                    $scope.changedMonitorType = function(type) {
                        // in this case I either chose for the first time or changed the monitor type ( array / vol )

                        // setup the list of metric for dropdown
                        $scope.setMetricNameList(type);

                        // now initialize other vars
                        // these should get set when chose a metric from the dropdown
                        $scope.selectedMetric.name = "";
                        $scope.selectedMetric.unit = "";
                        $scope.selectedMetric.metricUnitList = [];
                        $scope.selectedMetric.metricUnitString = "";
                        $scope.selectedMetric.value = "";

                    }

                    $scope.changedMetricName = function(name) {
                        // ok now you have selected a metric or changed an existing one

                        // setup list of unit options 
                        $scope.setMetricUnitList(name);

                        // I selected a new kind of clear our any residual unit 
                        // I need this because there are some metrics with no "units"
                        // and won't be cleared by ng-init
                        // queue_depth and data_reduction for example. in all other cases 
                        // I am hoping the ng-init should do the right thing
                        $scope.selectedMetric.unit = "";

                    }


                    $scope.setMetricNameList = function(type) {
                        if( type == 'array' ) {
                            $scope.selectedMetric.metricNameList = [{ name : "usec_per_read_op" , label : 'Read Latency'},
                                { name : "usec_per_write_op", label :  'Write Latency'},
                                { name : "input_per_sec" , label : 'Write Bandwidth'},
                                { name : "output_per_sec", label :  'Read Bandwidth'},
                                { name : "reads_per_sec" , label : 'Read IOPS'},
                                { name : "writes_per_sec", label :  'Write IOPS'},
                                { name : "total" , label : 'Total Used Space'},
                                { name : "system", label :  'System Space'},
                                { name : "shared_space" , label : 'Shared Space'},
                                { name : "volumes", label :  'Unique Volume Space'},
                                { name : "free" , label : 'Free Space'},
                                { name : "data_reduction", label :  'Data Reduction'},
                                { name : "total_reduction", label :  'Total Reduction'},
                                { name : "queue_depth", label :  'Queue Depth'},
                                { name : "percent_free", label :  'Percent Free'}];
                        } else if (type == 'vol') {
                           $scope.selectedMetric.metricNameList = [{ name : "usec_per_read_op" , label : 'Read Latency'},
                                { name : "usec_per_write_op", label :  'Write Latency'},
                                { name : "input_per_sec" , label : 'Write Bandwidth'},
                                { name : "output_per_sec", label :  'Read Bandwidth'},
                                { name : "reads_per_sec" , label : 'Read IOPS'},
                                { name : "writes_per_sec", label :  'Write IOPS'},
                                { name : "total" , label : 'Total Used Space'},
                                { name : "volumes", label :  'Unique Volume Space'},
                                { name : "free" , label : 'Free Space'},
                                { name : "data_reduction", label :  'Data Reduction'},
                                { name : "total_reduction", label :  'Total Reduction'},
                                { name : "percent_free", label :  'Percent Free'}];
                        } else {
                            $scope.selectedMetric.metricNameList = []
                        }
                        
                    }

                    $scope.computeValue = function(unit, value) {
                        var i;
                        for ( i=0; i < $scope.selectedMetric.metricUnitList.length; i++ ) {
                            if( $scope.selectedMetric.metricUnitList[i].unit == unit ) {
                                return String(Number(value) * Number($scope.selectedMetric.metricUnitList[i].factor));
                            }
                        }
                        // if I don't find a conversion just return original value
                        return String(value);
                    }

                    $scope.setMetricUnitList = function(name) {
                        // setup units depending on selected metric


                        if (name == 'usec_per_write_op' || name == 'usec_per_read_op') {
                            $scope.selectedMetric.metricUnitList = [{unit : 'us' , label: 'us', factor: "1"},
                            {unit : 'ms' , label: 'ms', factor: "1000"},
                            {unit : 's' , label: 's', factor: "1000000"}
                            ];
                        } else if( name == 'input_per_sec' || name == 'output_per_sec' ) {
                            $scope.selectedMetric.metricUnitList = [{unit : 'b' , label: 'Bytes/s', factor:"1"},
                            {unit : 'kb' , label: 'KB/s', factor: "1024"},
                            {unit : 'mb' , label: 'MB/s', factor: "1048576"},
                            {unit : 'gb' , label: 'GB/s', factor: "1073741824"}
                            ];
                        } else if( name == 'total' || name == 'system' || name == 'shared_space' || name == 'volumes' || name == 'free') {
                            $scope.selectedMetric.metricUnitList = [{unit : 'b' , label: 'Bytes', factor: "1"},
                            {unit : 'kb' , label: 'KB', factor: "1024" },
                            {unit : 'mb' , label: 'MB' , factor:"1048576" },
                            {unit : 'gb' , label: 'GB', factor: "1073741824"},
                            {unit : 'tb' , label: 'TB', factor: "1099511627776"},
                            {unit : 'pb' , label: 'PB', factor: "1125899906842624"}
                            ];
                        } else if(name == 'data_reduction' || name == 'total_reduction') {
                            $scope.selectedMetric.metricUnitList = [];
                            $scope.selectedMetric.metricUnitString = "to 1";

                        } else if(name == 'percent_free' ){
                            $scope.selectedMetric.metricUnitList = [{unit: "%", label:"%", factor:"0.01"}];
                            $scope.selectedMetric.metricUnitString = "";

                        } else {
                            // unrecognized units
                            $scope.selectedMetric.metricUnitList = [];
                            $scope.selectedMetric.metricUnitString = "";
                        }
                    }


                    $scope.resetNewMonitor = function() {
                        $scope.newmonitor = { array_name: "*", vol_name: "*", window: "1", window_scope: "d", severity : "info", data_ttl : "90", frequency: "60" };
                        $scope.newmonitorError = {}; 
                        $scope.selectedMetric = { name:"undefined", unit:"undefined" };
                    }

                    $scope.setupMonitorAdd = function() {
                        $scope.resetNewMonitor();
                        $scope.setMetricNameList("");
                    }

                    $scope.addMonitor = function () {
                        $log.info('Adding monitor');

                        // make a quick clone of the new monitor object and modify the TTL to add 'days'
                        var cloneOfNewMonitor = JSON.parse(JSON.stringify($scope.newmonitor));
                        cloneOfNewMonitor.data_ttl = cloneOfNewMonitor.data_ttl + 'd';
                        cloneOfNewMonitor.window = cloneOfNewMonitor.window + cloneOfNewMonitor.window_scope
                        cloneOfNewMonitor.metric = $scope.selectedMetric.name
                        cloneOfNewMonitor.metric_unit = $scope.selectedMetric.unit
                        // compute the value for the query using the appropriate units
                        cloneOfNewMonitor.orig_value = cloneOfNewMonitor.value
                        cloneOfNewMonitor.value = $scope.computeValue($scope.selectedMetric.unit, cloneOfNewMonitor.value)

                        PureElkRestService.addMonitor(angular.toJson(cloneOfNewMonitor)).$promise.then(function(data){
                            // success handler
                            $('#modalNewMonitor').modal('hide');
                            $scope.reloadMonitor();
                        }, function(error) {
                            $scope.newmonitorError.message = error.data.message;
                        });
                    }

                    $scope.reloadMonitor = function () {
                        PureElkRestService.getMonitors().$promise.then(function(monitorData) {
                           $scope.puremonitors = monitorData;
                        });
                    }

                    $scope.reloadMonitor();
                    $interval($scope.reloadMonitor, 5000);

                    // every second go in there to update the monitor updated time (seconds ago)
                    $interval(function(){
                        for (var monitor in $scope.puremonitors) {
                            monitor.refresh_seconds_ago = Math.floor(new Date().getTime() / 1000 - monitor.task_timestamp)
                        }
                    }, 1000)

                    $scope.setupMonitorEdit = function(monitor) {
                        // set up a copy of the monitor to bind into the "edit monitor" view.
                        var editmonitor = $.extend(true, {}, monitor);

                        // intitialize all the selectedMetric stuff 
                        $scope.selectedMetric = { name:"undefined", unit:"undefined" };
                        // loop through metrics and setup model correctly
                        $scope.setMetricNameList(monitor.type)
                        // get name of metric and units from monitor
                        $scope.selectedMetric.name = monitor.metric
                        $scope.selectedMetric.unit = monitor.metric_unit

                        // now setup the unitList correctly for dropdown
                        $scope.setMetricUnitList($scope.selectedMetric.name)

                        if (!!monitor.data_ttl)
                        {
                            // Need to trim away the day unit string "d".
                            editmonitor.data_ttl = monitor.data_ttl.substring(0, monitor.data_ttl.length - 1);
                        }

                        if (!!monitor.window)
                        {
                            // Need to trim away the scope "d m h".
                            editmonitor.window = monitor.window.substring(0, monitor.window.length - 1);
                        }

                        // put original value back into "value" so it gets displayed / computed correctly in updateMonitor
                        editmonitor.value = monitor.orig_value

                        $scope.monitorEdit = {
                            original: monitor,
                            edit: editmonitor
                        };

                        


                        $scope.editmonitorError = {};
                    }

                    $scope.updateMonitor = function() {
                        $log.info('Updating monitor: ' + $scope.monitorEdit.original.id);
                        var original = $scope.monitorEdit.original;
                        var edit = JSON.parse(JSON.stringify($scope.monitorEdit.edit));

                        edit.data_ttl = edit.data_ttl + 'd';
                        edit.window = edit.window + edit.window_scope;
                        edit.metric = $scope.selectedMetric.name
                        edit.metric_unit = $scope.selectedMetric.unit
                        // compute the value for the query using the appropriate units
                        edit.orig_value = edit.value
                        edit.value = $scope.computeValue($scope.selectedMetric.unit, edit.value)

                
                        PureElkRestService.updateMonitor({monitorid: edit.id}, angular.toJson(edit))
                            .$promise.then(function(data){
                                // success handler
                                $('#modalEditMonitor').modal('hide');
                                $scope.reloadMonitor();
                            }, function(error) {
                                $scope.editmonitorError.message = error.data.message;
                            });
                    }
                });