from celery.utils.log import get_task_logger
import json
import datetime

from elasticsearch import Elasticsearch
from elasticsearch_dsl import Search, Q, A
from elasticsearch_dsl.query import MultiMatch 

from pureelk.monitorcontext import MonitorContext

# setup the mappings for the index
volmap = """
{
    "mappings" : {
        "volperf":{
            "properties":{
                "name":{"type":"string","index":"not_analyzed"},
                "vol_name":{"type":"string","index":"not_analyzed"},
                "array_name":{"type":"string","index":"not_analyzed"},
                "array_id":{"type":"string","index":"not_analyzed"}
            },
            "_ttl" : { "enabled" : true }
        }
    }
}
"""

hostmap = """
{
    "mappings" : {
        "hostdoc":{
            "properties":{
                "name":{"type":"string","index":"not_analyzed"},
                "host_name":{"type":"string","index":"not_analyzed"},
                "array_name":{"type":"string","index":"not_analyzed"},
                "array_id":{"type":"string","index":"not_analyzed"}
            },
            "_ttl" : { "enabled" : true }
        }
    }
}
"""

hgroupmap = """
{
    "mappings" : {
        "hgroupdoc":{
            "properties":{
                "name":{"type":"string","index":"not_analyzed"},
                "hgroup_name":{"type":"string","index":"not_analyzed"},
                "array_name":{"type":"string","index":"not_analyzed"},
                "array_id":{"type":"string","index":"not_analyzed"}
            },
            "_ttl" : { "enabled" : true }
        }
    }
}
"""

arraymap = """
{
    "mappings" : {
        "arrayperf":{
            "properties":{
                "array_name":{"type":"string","index":"not_analyzed"},
                "array_id":{"type":"string","index":"not_analyzed"},
                "hostname":{"type":"string","index":"not_analyzed"}
            },
            "_ttl" : { "enabled" : true }
        }
    }
}
"""

msgmap = """
{
    "mappings" : {
        "arraymsg":{
            "properties":{
                "array_name":{"type":"string","index":"not_analyzed"},
                "array_id":{"type":"string","index":"not_analyzed"},
                "category":{"type": "string", "index": "not_analyzed"},
                "current_severity":{"type": "string", "index": "not_analyzed"},
                "actual":{"type": "string", "index": "not_analyzed"},
                "component_name":{"type": "string", "index": "not_analyzed"},
                "component_type":{"type": "string", "index": "not_analyzed"},
                "details":{"type": "string", "index": "not_analyzed"},
                "expected":{"type": "string", "index": "not_analyzed"},
                "event":{"type": "string", "index": "not_analyzed"}
            },
            "_ttl" : { "enabled" : true }
        }
    }
}
"""

auditmap = """
{
    "mappings" : {
        "auditmsg":{
            "properties":{
                "array_name":{"type":"string","index":"not_analyzed"},
                "array_id":{"type":"string","index":"not_analyzed"},
                "component_name":{"type":"string","index":"not_analyzed"},
                "component_type":{"type":"string","index":"not_analyzed"},
                "details":{"type":"string","index":"not_analyzed"},
                "event":{"type":"string","index":"not_analyzed"},
                "user":{"type":"string","index":"not_analyzed"}
            },
            "_ttl" : { "enabled" : true }
        }
    }
}
"""

class PureCollector(object):
    _timeofquery_key = 'timeofquery'

    def __init__(self, ps_client, es_client, array_context):
        self._ps_client = ps_client;
        self._es_client = es_client;
        self._array_name = array_context.name
        self._array_id = array_context.id
        self._data_ttl = array_context.data_ttl
        self.logger = get_task_logger(__name__)

    def collect(self):
        utcnow = datetime.datetime.utcnow()

        date_str = utcnow.strftime('%Y-%m-%d')
        arrays_index = "pureelk-arrays-{}".format(date_str)
        vols_index = "pureelk-vols-{}".format(date_str)
        hosts_index = "pureelk-hosts-{}".format(date_str)
        hgroups_index = "pureelk-hgroup-{}".format(date_str)
        msgs_index = "pureelk-msgs-{}".format(date_str)
        audit_index = "pureelk-audit-{}".format(date_str)
        global_arrays_index = "pureelk-global-arrays"
        global_vols_index = "pureelk-global-vols"

        # ignore indices already exists error (code 409)
        self._es_client.indices.create(index=vols_index, body=volmap, ignore=[400, 409])
        self._es_client.indices.create(index=arrays_index, body=arraymap, ignore=[400, 409])
        self._es_client.indices.create(index=msgs_index, body=msgmap, ignore=[400, 409])
        self._es_client.indices.create(index=audit_index, body=auditmap, ignore=[400, 409])
        self._es_client.indices.create(index=hosts_index, body=hostmap, ignore=[400, 409])
        self._es_client.indices.create(index=hgroups_index, body=hgroupmap, ignore=[400, 409])


        #special non-time series stash of array/vol documents
        self._es_client.indices.create(index=global_arrays_index, body=arraymap, ignore=[400, 409])
        self._es_client.indices.create(index=global_vols_index, body=volmap, ignore=[400, 409])

        # all metrics collected in the same cycle are posted to Elasticsearch with same timestamp
        timeofquery_str = utcnow.isoformat()

        # get the overall array info for performance
        ap = self._ps_client.get(action='monitor')
        ap[0]['array_name'] = self._array_name
        ap[0]['array_id'] = self._array_id
        # add an array name that elasticsearch can tokenize ( i.e. won't be present in mappings above )
        ap[0]['array_name_a'] = self._array_name

        # now get the information for space
        sp = self._ps_client.get(space=True)
        nd = sp.copy()

        # copy items into the new dictionary
        ap[0].update(nd)

        # add some pre-calc'd fields so Kibana doesn't need scripted fields. That makes install less
        # one button if we include them
        cap = long(ap[0]['capacity'])
        tot = long(ap[0]['total'])
        ap[0]['free'] = cap - tot
        ap[0]['percent_free'] = (float(cap) - float(tot)) / float(cap)

        ap[0][PureCollector._timeofquery_key] = timeofquery_str
        s = json.dumps(ap[0])
        self._es_client.index(index=arrays_index, doc_type='arrayperf', body=s, ttl=self._data_ttl)

        # non-timeseries array docs, uses id to bring es versioning into play
        self._es_client.index(index=global_arrays_index, doc_type='arrayperf', body=s, id=self._array_id, ttl=self._data_ttl)


        # index alert messages
        al = self._ps_client.list_messages(recent='true')
        for am in al:
            am['array_name'] = self._array_name
            am['array_id'] = self._array_id
            # add an array name  that elasticsearch can tokenize ( i.e. won't be present in mappings above )
            am['array_name_a'] = self._array_name
            am[PureCollector._timeofquery_key] = timeofquery_str
            s = json.dumps(am)
            self._es_client.index(index=msgs_index, doc_type='arraymsg', id=am['id'], body=s, ttl=self._data_ttl)

        # index audit log entries
        al = self._ps_client.list_messages(audit='true')
        for am in al:
            am['array_name'] = self._array_name
            am['array_id'] = self._array_id
            # add an array name  that elasticsearch can tokenize ( i.e. won't be present in mappings above )
            am['array_name_a'] = self._array_name
            am[PureCollector._timeofquery_key] = timeofquery_str
            s = json.dumps(am)
            self._es_client.index(index=audit_index, doc_type='auditmsg', id=am['id'], body=s, ttl=self._data_ttl)

        # get list of volumes
        vl = self._ps_client.list_volumes()

        for v in vl:
            # get real-time perf stats per volume
            vp = self._ps_client.get_volume(v['name'], action='monitor')
            vp[0]['array_name'] = self._array_name
            vp[0]['array_id'] = self._array_id
            vp[0]['vol_name'] = self._array_name + ':' + v['name']
            
            # add an array name and a volume name that elasticsearch can tokenize ( i.e. won't be present in mappings above )
            vp[0]['vol_name_a'] = v['name']
            vp[0]['array_name_a'] = self._array_name
            
            vp[0][PureCollector._timeofquery_key] = timeofquery_str
            
            # get space stats per volume and append 
            vs = self._ps_client.get_volume(v['name'], space=True)
            vp[0].update(vs)

            # get the host and host group connections per volume
            # create a large string that we are hoping elasticsearch
            # will tokenize and help us match
            hs =""
            hgs=""
            hp = self._ps_client.list_volume_private_connections(v['name'])
            for h in hp:
                if h['host']:
                    hs += h['host']
                    hs += ' '

            hglist = []
            hp = self._ps_client.list_volume_shared_connections(v['name'])
            for hg in hp:
                if hg['host']:
                    hs += hg['host']
                    hs += ' '
                if hg['hgroup'] and hg['hgroup'] not in hglist:
                    # only include unique host group names 
                    hglist.append(hg['hgroup'])
                    hgs += hg['hgroup']
                    hgs += ' '

            vp[0]['host_name'] = hs
            vp[0]['hgroup_name'] = hgs

            # get the serial number for this volume to use as a unique global id
            vp1 = self._ps_client.get_volume(v['name'])
            vp[0]['serial'] = vp1['serial']
            
            # dump total document into json
            s = json.dumps(vp[0])
            self._es_client.index(index=vols_index, doc_type='volperf', body=s, ttl=self._data_ttl)

            # non-timeseries volume docs, uses id to bring es versioning into play, uses serial number as global ID
            self._es_client.index(index=global_vols_index, doc_type='volperf', body=s, id=vp1['serial'], ttl=self._data_ttl)

        # get list of hosts
        hl = self._ps_client.list_hosts()

        for h in hl:
            # get real-time perf stats per host
            hp = self._ps_client.get_host(h['name'], space=True)
            hp['array_name'] = self._array_name
            hp['array_id'] = self._array_id
            hp['host_name'] = h['name']
            hp['hgroup_name'] = h['hgroup']
            # add an array name and a volume name that elasticsearch can tokenize ( i.e. won't be present in mappings above )
            hp['host_name_a'] = h['name']
            hp['array_name_a'] = self._array_name
            hp[PureCollector._timeofquery_key] = timeofquery_str

            # dump total document into json
            s = json.dumps(hp)
            self._es_client.index(index=hosts_index, doc_type='hostdoc', body=s, ttl=self._data_ttl)

        # get list of host groups
        hl = self._ps_client.list_hgroups()

        for hg in hl:
            # get real-time perf stats per host group
            hgp = self._ps_client.get_hgroup(hg['name'], space=True)
            hgp['array_name'] = self._array_name
            hgp['array_id'] = self._array_id
            hgp['hgroup_name'] = hg['name']
            # add an array name and a volume name that elasticsearch can tokenize ( i.e. won't be present in mappings above )
            hgp['hgroup_name_a'] = hg['name']
            hgp['array_name_a'] = self._array_name
            hgp[PureCollector._timeofquery_key] = timeofquery_str

            # include a reference to all hosts in the group at the time of this call
            hgl = self._ps_client.get_hgroup(hg['name'])
            hls = ""
            for h in hgl['hosts']:
                hls += h
                hls += ' '
            hgp['host_name'] = hls

           # dump total document into json
            s = json.dumps(hgp)
            self._es_client.index(index=hgroups_index, doc_type='hgroupdoc', body=s, ttl=self._data_ttl)


class PureArrayMonitor(object):
    _timeofquery_key = 'timeofquery'
    

    # init basic elasticsearch client and monitor context
    def __init__(self, es_client, monitor_context):
        self._es_client = es_client;
        self.logger = get_task_logger(__name__)
        self._monitor = monitor_context
        self._utcnow = datetime.datetime.utcnow()
        self._date_str = self._utcnow.strftime('%Y-%m-%d')
        self._msgs_index = "pureelk-msgs-{}".format(self._date_str)
        self._timeofquery_str = self._utcnow.isoformat()

    # run the query for the monitor and process results
    def monitor(self):

        self.logger.info("Running PureArrayMonitor")

        #create a Search object
        s = Search(using=self._es_client)
        s = s.index("pureelk-arrays-*")
        s = s.query(Q("wildcard", array_name=self._monitor.array_name))

        # apply time window filter on query
        s = s.filter('range',timeofquery={'lt':'now','gte': 'now-{}'.format(self._monitor.window)})

        # now apply the metric we want to monitor for
        s = s.query('range',**{ self._monitor.metric : { self._monitor.compare: self._monitor.value} })

        #now bucketize the results to make so we can access 'hits' per object
        a = A('terms', field='array_name')
        t = A('top_hits', size=1, sort=[{'timeofquery': {'order':'desc'}}], _source=['array_id','array_name','timeofquery'])
        s.aggs.bucket('per_array_name',a).bucket('top_array_hits', t)

        # dump query to log
        self.logger.info("Query executed {} ".format(s.to_dict()))

        # execute the query and check for relevant hits
        r = s.execute()

        # loop through buckets and see if anyone has enough "hits"
        for b in r.aggregations.per_array_name.buckets:
            if b['doc_count'] >= self._monitor.hits:
                # this means that monitor query had a number of hits over the threshold established by the user
                self.logger.info("PureArrayMonitor had {} hits".format(b['doc_count']))

                # debug log the bucket contents
                self.logger.info(b)

                 # create a "alert document" and deposit it in correct index
                self._user_defined_message(b)

    # create a new document and insert into messages
    # index of pureelk, customer will be able to see it 
    # in normal location for alerts
    def _user_defined_message(self, bucket):
        # create a 'message' document that will look like a array_message document
        am = {}
        # extract array_from document in the top_hits bucket 
        am['array_name'] = bucket['top_array_hits']['hits']['hits'][0]['_source']['array_name']
        am['array_id'] = bucket['top_array_hits']['hits']['hits'][0]['_source']['array_id']
        am['array_name_a'] = am['array_name']
        am[PureArrayMonitor._timeofquery_key] = self._timeofquery_str
        am['category'] = 'user_defined'
        am['current_severity'] = self._monitor.severity
        am['actual'] = "{} Matching Samples".format(bucket['doc_count'])
        am['details'] = "User defined alert message for {}".format(bucket['key'])
        am['event'] = "Monitor triggered"
        am['expected'] = "{} not {} {}".format(self._monitor.metric, self._monitor.compare, self._monitor.value)
        am['component_name'] = "array.user_defined"
        ms = json.dumps(am)
        res = self._es_client.index(index=self._msgs_index, doc_type='arraymsg', body=ms, ttl=self._monitor.data_ttl)



class PureVolumeMonitor(object):
    _timeofquery_key = 'timeofquery'

    # init basic elasticsearch client and monitor context
    def __init__(self, es_client, monitor_context):
        self._es_client = es_client;
        self.logger = get_task_logger(__name__)
        self._monitor = monitor_context
        self._utcnow = datetime.datetime.utcnow()
        self._date_str = self._utcnow.strftime('%Y-%m-%d')
        self._msgs_index = "pureelk-msgs-{}".format(self._date_str)
        self._timeofquery_str = self._utcnow.isoformat()

    # run the query for the monitor and process results
    def monitor(self):

        self.logger.info("Running PureVolumeMonitor")

        # create a Search object
        s = Search(using=self._es_client)
        s = s.index("pureelk-vols-*")
        # create an "AND" query to make sure if someone specified a specific volume on a specific
        # array it will work. ES wildcard will make this super powerful
        # I am consciously not using "vol_name" because it also includes the array name
        # I use vol_name below when I want unique buckets for hits
        s = s.query(Q("wildcard", array_name=self._monitor.array_name) & Q("wildcard", vol_name=self._monitor.vol_name))

        # apply time window filter on query
        s = s.filter('range',timeofquery={'lt':'now','gte': 'now-{}'.format(self._monitor.window)})

        # now apply the metric we want to monitor for
        s = s.query('range',**{ self._monitor.metric : { self._monitor.compare: self._monitor.value} })

        # now bucketize the results to make it so we can access 'hits' per volume
        # this name specifically has <array_name>:<vol_name> in it so the buckets 
        # should be unique per volume across all arrays
        a = A('terms', field='vol_name')
        t = A('top_hits', size=1, sort=[{'timeofquery': {'order':'desc'}}],_source=['array_id','array_name','name','timeofquery'])
        s.aggs.bucket('per_vol_name',a).bucket('top_vol_hits', t) 

        # dump query to log
        self.logger.info("Query executed {} ".format(s.to_dict()))

        # execute the query and check for relevant hits
        r = s.execute()

        # loop through buckets and see if anyone has enough "hits"
        for b in r.aggregations.per_vol_name.buckets:
            if b['doc_count'] >= self._monitor.hits:
                # this means that monitor query had a number of hits over the threshold established by the user
                self.logger.info("{} hits ".format(b['doc_count']))

                # now query the message documents and see if this monitor already fired this alert 
                # based on the 'latest' document ( which basically means I am ringing the bell again
                # for the same thing ). I get the 'latest' document because of the sort order I set
                # in the query above.
                # if _find_message_document( self._monitor.id, ['top_vol_hits']['hits']['hits'][0]['_source']['_id'])

                # debug log the bucket 
                self.logger.info(b)

                # create a "alert document" and deposit it in correct index
                self._user_defined_message(b)

    
    # create a new document and insert into messages
    # index of pureelk, customer will be able to see it 
    # in normal location for alerts
    def _user_defined_message(self, bucket):
        # create a 'message' document that will look like a array_message document
        am = {}
        # extract array_from document in the top_hits bucket 
        am['array_name'] = bucket['top_vol_hits']['hits']['hits'][0]['_source']['array_name']
        am['array_id'] = bucket['top_vol_hits']['hits']['hits'][0]['_source']['array_id']
        am['array_name_a'] = am['array_name']
        am[PureArrayMonitor._timeofquery_key] = self._timeofquery_str
        am['actual'] = "{} Matching Samples".format(bucket['doc_count'])
        am['category'] = 'user_defined'
        am['current_severity'] = self._monitor.severity
        am['details'] = "User defined alert message for {}".format(bucket['key'])
        am['event'] = "Monitor triggered"
        am['expected'] = "{} not {} {}".format(self._monitor.metric, self._monitor.compare, self._monitor.value)
        am['component_name'] = "volume.user_defined"
        ms = json.dumps(am)
        res = self._es_client.index(index=self._msgs_index, doc_type='arraymsg', body=ms, ttl=self._monitor.data_ttl)


    '''
    "category": "array",
        "array_id": "8f57327e-68ee-7599-063a-53fadd8eb2f6",
        "array_name_a": "dogfood1492",
        "code": 25,
        "actual": "80.08%",
        "opened": "2016-02-19T02:03:05Z",
        "component_type": "storage",
        "array_name": "dogfood1492",
        "id": 677696,
        "timeofquery": "2016-02-21T21:52:11.281464",
        "current_severity": "info",
        "details": "",
        "expected": "< 90.00%",
        "event": "high utilization",
        "component_name": "array.capacity"
    '''
