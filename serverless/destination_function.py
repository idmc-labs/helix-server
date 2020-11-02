import logging
import os
import json

import requests

logger = logging.getLogger(__name__)


def handle(event, context):
    url = os.environ.get('WEBHOOK_URL')
    r = requests.post(url, data={'event': json.dumps(event)})
    # for the purpose of logging
    logger.info(json.dumps(event))
    logger.info('Sent filename to %s. Got %d response.' % (url, r.status_code))
