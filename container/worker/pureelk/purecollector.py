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
                "name":{"type":"string","index":"not_analyzed"},
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
        msgs_index = "pureelk-msgs-{}".format(date_str)
        audit_index = "pureelk-audit-{}".format(date_str)

        # ignore indices already exists error (code 409)
        self._es_client.indices.create(index=vols_index, body=volmap, ignore=[400, 409])
        self._es_client.indices.create(index=arrays_index, body=arraymap, ignore=[400, 409])
        self._es_client.indices.create(index=msgs_index, body=msgmap, ignore=[400, 409])
        self._es_client.indices.create(index=audit_index, body=auditmap, ignore=[400, 409])


        # all metrics collected in the same cycle are posted to Elasticsearch with same timestamp
        timeofquery_str = utcnow.isoformat()

        # get the overall array info for performance
        ap = self._ps_client.get(action='monitor')
        ap[0]['name'] = self._array_name
        ap[0]['array_id'] = self._array_id

        # now get the information for space
        sp = self._ps_client.get(space=True)
        nd = sp.copy()

        # copy items into the new dictionary
        ap[0].update(nd)
        ap[0][PureCollector._timeofquery_key] = timeofquery_str
        s = json.dumps(ap[0])
        self._es_client.index(index=arrays_index, doc_type='arrayperf', body=s, ttl=self._data_ttl)

        # index alert messages
        al = self._ps_client.list_messages(recent='true')
        for am in al:
            am['array_name'] = self._array_name
            am['array_id'] = self._array_id
            am[PureCollector._timeofquery_key] = timeofquery_str
            s = json.dumps(am)
            self._es_client.index(index=msgs_index, doc_type='arraymsg', id=am['id'], body=s, ttl=self._data_ttl)

        # index alert messages
        al = self._ps_client.list_messages(audit='true')
        for am in al:
            am['array_name'] = self._array_name
            am['array_id'] = self._array_id
            am[PureCollector._timeofquery_key] = timeofquery_str
            s = json.dumps(am)
            self._es_client.index(index=audit_index, doc_type='auditmsg', id=am['id'], body=s, ttl=self._data_ttl)

        # get list of volumes
        vl = self._ps_client.list_volumes()

        for v in vl:
            vp = self._ps_client.get_volume(v['name'], action='monitor')
            vp[0]['array_name'] = self._array_name
            vp[0]['array_id'] = self._array_id
            vp[0][PureCollector._timeofquery_key] = timeofquery_str
            s = json.dumps(vp[0])
            self._es_client.index(index=vols_index, doc_type='volperf', body=s, ttl=self._data_ttl)
