import base64
import math
import logging

from billiard.exceptions import TimeLimitExceeded
from django.core.files.base import ContentFile
from selenium import webdriver
from selenium.webdriver.support.ui import WebDriverWait
from selenium.common.exceptions import TimeoutException

from helix.celery import app as celery_app
# from helix.settings import QueuePriority

logger = logging.getLogger(__name__)
PDF_TASK_TIMEOUT = 30  # seconds
SELENIUM_TIMEOUT = math.floor(PDF_TASK_TIMEOUT * 0.8)


def __get_pdf_from_html(path, timeout=SELENIUM_TIMEOUT, print_options={}):
    browser_options = webdriver.ChromeOptions()
    # browser_options.add_argument('no-sandbox')
    # Don't add no-sandbox option,
    # Reference https://stackoverflow.com/questions/60101367/security-considerations-chromedriver-webdriver-for-chrome
    browser_options.add_argument('headless')
    browser_options.add_argument('disable-gpu')
    browser_options.add_argument('disable-dev-shm-usage')

    browser = webdriver.Chrome(options=browser_options)

    browser.get(path)

    try:
        WebDriverWait(browser, timeout).until(lambda d: d.execute_script('return document.readyState') == 'complete')
    except TimeoutException:
        logger.error(f'Chromium timed out for {path}. Saving as is...', exc_info=True)
    except TimeLimitExceeded:
        logger.error(f'Selenium timed out for {path}. Saving as is...', exc_info=True)

    final_print_options = {
        'landscape': False,
        'displayHeaderFooter': False,
        'printBackground': True,
        'preferCSSPageSize': True,
    }
    final_print_options.update(print_options)

    result = browser.execute_cdp_cmd("Page.printToPDF", final_print_options)
    browser.quit()
    return base64.b64decode(result['data'])


@celery_app.task(time_limit=PDF_TASK_TIMEOUT)
def generate_pdf(pk):
    from apps.contrib.models import SourcePreview

    source_preview = SourcePreview.objects.get(pk=pk)
    url = source_preview.url
    path = f'{source_preview.token}.pdf'
    logger.warn(f'Starting pdf generation for url: {url} and preview id: {source_preview.id}.')

    source_preview.status = SourcePreview.PREVIEW_STATUS.IN_PROGRESS
    source_preview.save()

    try:
        pdf_content = __get_pdf_from_html(url)
        source_preview.pdf.save(path, ContentFile(pdf_content))
        source_preview.status = SourcePreview.PREVIEW_STATUS.COMPLETED
        source_preview.save()
        logger.warn(f'Completed pdf generation for url: {url} and preview id: {source_preview.id}.')
    except Exception as e:  # noqa
        logger.error('An exception occurred', exc_info=True)
        source_preview.status = SourcePreview.PREVIEW_STATUS.FAILED
        source_preview.save()
        raise e
