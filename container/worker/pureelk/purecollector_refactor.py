import abc

class PureMonitor(object):
    __metaclass__ = abc.ABCMeta

    def __init__(self, es_client, monitor_context):
        # init some variables
        self.logger = get_task_logger(__name__)
        self._monitor = monitor_context
        self._utcnow = datetime.datetime.utcnow()
        self._date_str = self._utcnow.strftime('%Y-%m-%d')
        self._msgs_index = "pureelk-msgs-{}".format(self._date_str)
        self._timeofquery_str = self._utcnow.isoformat()
        self._am = {}

        # stash the elasticsearch client
        self._es_client = es_client;
        # setup search query
        self._search_query = Search(using=self._es_client)
        self._response = None

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
        am = self._am

        # extract some standard fields from document
        th = self._bucket_hits(b)
        am['array_name'] = th['_source']['array_name']
        am['array_id'] = th['_source']['array_id']
        am['array_name_a'] = am['array_name']

        # put monitor id and latest "hit" in message, this helps stop excessive message creation
        # (see _is_repeat_message()
        am['details'] = "{} {}".format(self._monitor.id, th['_id'])
        
        am[PureArrayMonitor._timeofquery_key] = self._timeofquery_str
        am['category'] = 'user_defined'
        am['current_severity'] = self._monitor.severity
        am['actual'] = "{} docs matched monitor in {}".format(b['doc_count'], self._monitor.window)
        
        
        am['expected'] = "{} not {} {}".format(self._monitor.metric, self._monitor.compare, self._monitor.value)
        
        # subclass can add some fields like component_name 
        am = self._pack_other_message_fields()

    def send_user_defined_message(self):

        ms = json.dumps(self_._am)
        res = self._es_client.index(index=self._msgs_index, doc_type='arraymsg', body=ms, ttl=self._monitor.data_ttl)


    @abc.abstractmethod
    def _set_index(self):
        return

    @abc.abstractmethod
    def _field_name(self):
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

    

class PureArrayMonitor(PureMonitor):

    def _set_index(self):
        self._search_query = self._search_query.index("pureelk-arrays-*")
        return

    def _field_name(self):
        return 'array_name'

    def _set_scope(self):
        self._search_query = self._search_query.query(Q("wildcard", array_name=self._monitor.array_name))
        return

    def _pack_other_message_fields(self):
        self._am['component_name'] = 'array.user_defined'

class PureVolumeMonitor(PureMonitor):

    def _set_index(self):
        self._search_query = self._search_query.index("pureelk-vols-*")
        return

    def _field_name(self):
        return 'vol_name'

    def _pack_other_message_fields(self):
        self._am['component_name'] = 'volume.user_defined'

