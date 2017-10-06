import sys
from elasticsearch import Elasticsearch
import time
import requests
import logging

ES_ENDPOINT = "pureelk-elasticsearch:9200"
logging.basicConfig(stream=sys.stdout, level=logging.INFO)

def check_es_endpoint():
    attempts = 3
    while attempts > 0:
        time.sleep(5)
        status_code = 0

        try: 
            r = requests.get("http://{}".format(ES_ENDPOINT), timeout=5)
            status_code = r.status_code
        except Exception as e: 
            logging.info("Error encountered when trying to connect to {}: {}".format(ES_ENDPOINT, e))

        if status_code == 200:
            logging.info("Successfully connected to elasticsearch endpoint at {}".format(ES_ENDPOINT))
            break
        else:     
            attempts -= 1
            logging.info("Not able to connect to {}, status code: {}, attempts remaining: {}".format(
                ES_ENDPOINT, 
                status_code,
                attempts))

    return attempts > 0


if __name__ == '__main__':
    exists = check_es_endpoint()
    if exists:
        # create a connection to the Elasticsearch database
        client = Elasticsearch([ES_ENDPOINT], retry_on_timeout=True)
        if client.exists(index='.kibana', doc_type='index-pattern',id='pureelk-global-arrays'):
            logging.info("PureELK index patterns already exist.")
            sys.exit(0)
        else:
            logging.info("PureElk index patterns do not exist yet.")
            sys.exit(1)
    else:
        sys.exit(2)
        