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


                    $scope.resetNewMonitor = function() {
                        $scope.newmonitor = { array_name: "*", vol_name: "*", window: "1", window_scope: "d", severity : "info", data_ttl : "90", frequency: "60" };
                        $scope.newmonitorError = {};
                    }

                    $scope.setupMonitorAdd = function() {
                        $scope.resetNewMonitor();
                    }

                    $scope.addMonitor = function () {
                        $log.info('Adding monitor');

                        // make a quick clone of the new monitor object and modify the TTL to add 'days'
                        var cloneOfNewMonitor = JSON.parse(JSON.stringify($scope.newmonitor));
                        cloneOfNewMonitor.data_ttl = cloneOfNewMonitor.data_ttl + 'd';


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

                        if (!!monitor.data_ttl)
                        {
                            // Need to trim away the day unit string "d".
                            editmonitor.data_ttl = monitor.data_ttl.substring(0, monitor.data_ttl.length - 1);
                        }

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