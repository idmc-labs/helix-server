import dramatiq
import logging

logger = logging.getLogger(__name__)


@dramatiq.actor
def generate_log(pk):
    print(f'Generating log not in foreground for "{pk}."')
