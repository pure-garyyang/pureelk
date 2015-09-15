__author__ = 'terry'

import sys
from elasticsearch import Elasticsearch
import time

if __name__ == '__main__':

    time.sleep(5)
    # create a connection to the Elasticsearch database
    client = Elasticsearch(['pureelk-elasticsearch:9200'], retry_on_timeout=True)

    if client.indices.exists(index='pureelk-global-arrays'):
        sys.exit(0)
    else:
        sys.exit(1)