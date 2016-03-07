from celery.utils.log import get_task_logger
import json
import datetime

from elasticsearch import Elasticsearch
from elasticsearch_dsl import Search, Q, A
from elasticsearch_dsl.query import MultiMatch 

from pureelk.monitorcontext import MonitorContext

import abc

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


class PureMonitor(object):
    __metaclass__ = abc.ABCMeta
    _timeofquery_key = 'timeofquery'

    def __init__(self, es_client, monitor_context):
        # init some variables
        self.logger = get_task_logger(__name__)
        self._monitor = monitor_context
        self._utcnow = datetime.datetime.utcnow()
        self._date_str = self._utcnow.strftime('%Y-%m-%d')
        self._msgs_index = "pureelk-msgs-{}".format(self._date_str)
        self._timeofquery_str = self._utcnow.isoformat()
        self._am = {}
        self._timeofquery_key = 'timeofquery'

        # stash the elasticsearch client
        self._es_client = es_client;
        # setup search query
        self._search_query = Search(using=self._es_client)
        self._response = None

    @abc.abstractmethod
    def _set_index(self):
        return

    @abc.abstractmethod
    def _field_name(self):
        return

    def _pack_other_message_fields(self):
        return

    def _buckets_string(self):
        return "PureMonitor_field"

    def _hits_string (self):
        return "PureMonitor_hits"

    def _response_buckets(self):
        return  self._response.aggregations.PureMonitor_field.buckets

    def _bucket_hits(self, b):
        return  b['PureMonitor_hits']['hits']['hits']

    def _set_scope(self):
        # default scope to do array and volume names
        self._search_query = self._search_query.query(Q("wildcard", array_name=self._monitor.array_name) & Q("wildcard", vol_name=self._monitor.vol_name))

    def _set_time_window(self):
        #should be default implementation of time window
        self._search_query = self._search_query.filter('range',timeofquery={'lt':'now','gte': 'now-{}'.format(self._monitor.window)})

    def _apply_metric(self):
        # add the appropriate metric evaluation to the query
        self._search_query = self._search_query.query('range',**{ self._monitor.metric : { self._monitor.compare: self._monitor.value} })

    def _setup_buckets(self):
        a = A('terms', field=self._field_name())
        t = A('top_hits', size=1, sort=[{'timeofquery': {'order':'desc'}}])
        self._search_query.aggs.bucket("{}".format(self._buckets_string()),a).bucket("{}".format(self._hits_string()), t)


    def monitor(self):
        self.logger.info("Running PureMonitor")

        # I've setup a basic flow to create the search query and parse its results so 
        # it can be subclassed effectively. some things are abstract methods that need to be
        # overridden other things are optional

        # extend the search object with the correct index , happens in subclass
        self._set_index()

        # now setup the scope of the query ,there will be a default implementation in base class
        # ( array_name = <regexp> & vol_name = <regexp> )
        self._set_scope() 

        # apply time window filter on query
        self._set_time_window()

        # now apply the metric we want to monitor for
        self._apply_metric()

        #now bucketize the results to make so we can access 'hits' per object
        # expected to be implemented in subclass
        self._setup_buckets()
        
        # dump query to log
        self.logger.info("PureMonitor Query executed {} ".format(self._search_query.to_dict()))

        # execute the query
        self._response = self._search_query.execute()

        # deal with the query results, the default implementaion will be provided that 
        # handles most of the generic workflow of assessing hits and sending a 'user_defined'
        # alert message
        self._process_results()

    def _process_results(self):

        # base class workflow to fire a monitor if enough hits are found in any buckets

        # loop through buckets and see if anyone has enough "hits"
        buckets = self._response_buckets()
        for b in buckets:
            if b['doc_count'] >= self._monitor.hits:
                # this means that monitor query had a number of hits over the threshold established by the user
                self.logger.info("PureMonitor: {} hits ".format(b['doc_count']))

                # now query the message documents and see if this monitor already fired this alert 
                # based on the 'latest' document. Unless I get new "hits for the query" I'll be creating 
                # a new message alert for every collection interval. I tucked the monitor_id (uuid) and 
                # the document id in the alert message for this reason
                if self._is_repeat_message(b):
                    self.logger.info("PureMonitor: Skipping repeat message creation for {}".format(b['key']))
                    continue

                # create a "alert document" and deposit it in correct index
                self._user_defined_message(b)
    
    def _is_repeat_message(self,b):

         #create a new search object
        ms = Search(using=self._es_client)

        ms = ms.index("pureelk-msgs-*")

        # look for both uuid and document id in first document returned
        # thiscounts on sort order of documents ( kind of ) 
        h = self._bucket_hits(b)
        ms = ms.query(Q("wildcard", details="*{}*{}*".format(self._monitor.id,h[0]['_id'])))

        # apply time window filter on query , this is just meant to help restrict query to a limited 
        # number of documents to speed up check. 
        ms = ms.filter('range',timeofquery={'lt':'now','gte': 'now-{}'.format(self._monitor.window)})

        res = ms.execute()
        
        if res.hits.total > 0:
            # a document was found that is a duplidate for this monitor
            # don't create another message
            return True

        return False

    def _user_defined_message(self, b):
        # create a 'message' document that will look like a array_message document
        # and insert it into elasticsearch index

        # extract some standard fields from document
        hits = self._bucket_hits(b)
        th = hits[0]
        self._am['array_name'] = th['_source']['array_name']
        self._am['array_id'] = th['_source']['array_id']
        self._am['array_name_a'] = self._am['array_name']

        # put monitor id and latest "hit" in message, this helps stop excessive message creation
        # (see _is_repeat_message()
        self._am['details'] = "{} {}".format(self._monitor.id, th['_id'])
        
        self._am[self._timeofquery_key] = self._timeofquery_str
        self._am['category'] = 'user_defined'
        self._am['current_severity'] = self._monitor.severity
        self._am['actual'] = "{} docs matched in {}".format(b['doc_count'], self._monitor.window) 
        self._am['expected'] = "{} not {} {}".format(self._monitor.metric, self._monitor.compare, self._monitor.value)
        
        # subclass can add some fields like component_name or possible override fields packed above
        self._pack_other_message_fields(b)

        ms = json.dumps(self._am)
        res = self._es_client.index(index=self._msgs_index, doc_type='arraymsg', body=ms, ttl=self._monitor.data_ttl)

    

class PureArrayMonitor(PureMonitor):

    def _set_index(self):
        self._search_query = self._search_query.index("pureelk-arrays-*")
        return

    def _field_name(self):
        return 'array_name'

    def _set_scope(self):
        self._search_query = self._search_query.query(Q("wildcard", array_name=self._monitor.array_name))
        return

    def _pack_other_message_fields(self,b):
        self._am['component_name'] = 'array.user_defined'

class PureVolumeMonitor(PureMonitor):

    def _set_index(self):
        self._search_query = self._search_query.index("pureelk-vols-*")
        return

    def _field_name(self):
        return 'vol_name'

    def _pack_other_message_fields(self,b):
        self._am['component_name'] = 'volume.user_defined'
