import os
import json

import requests


def handle(event, context):
    url = os.environ.get('WEBHOOK_URL')
    r = requests.post(url, data={'event': json.dumps(event)})
    # for the purpose of logging
    print(event)
    print(url, r.status_code)
