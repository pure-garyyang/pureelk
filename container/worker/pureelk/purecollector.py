from celery.utils.log import get_task_logger
import json
import datetime


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

        # ignore indices already exists error (code 409)
        self._es_client.indices.create(index=vols_index, body=volmap, ignore=[400, 409])
        self._es_client.indices.create(index=arrays_index, body=arraymap, ignore=[400, 409])
        self._es_client.indices.create(index=msgs_index, body=msgmap, ignore=[400, 409])
        self._es_client.indices.create(index=audit_index, body=auditmap, ignore=[400, 409])
        self._es_client.indices.create(index=hosts_index, body=hostmap, ignore=[400, 409])
        self._es_client.indices.create(index=hgroups_index, body=hgroupmap, ignore=[400, 409])


        #special non-time series stash of array documents
        self._es_client.indices.create(index=global_arrays_index, body=arraymap, ignore=[400, 409])

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
            vp[0]['vol_name'] = v['name']
            
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
                hs += h['host']
                hs += ' '

            hp = self._ps_client.list_volume_shared_connections(v['name'])
            for hg in hp:
                hs += hg['host']
                hs += ' '
                hgs += hg['hgroup']
                hgs += ' '

            vp[0]['host_name'] = hs
            vp[0]['hgroup_name'] = hgs
            
            # dump total document into json
            s = json.dumps(vp[0])
            self._es_client.index(index=vols_index, doc_type='volperf', body=s, ttl=self._data_ttl)


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

           # dump total document into json
            s = json.dumps(hgp)
            self._es_client.index(index=hgroups_index, doc_type='hgroupdoc', body=s, ttl=self._data_ttl)
