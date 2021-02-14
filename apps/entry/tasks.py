import base64
import logging

import dramatiq
from dramatiq.middleware import TimeLimitExceeded
from django.core.files.base import ContentFile
from selenium import webdriver
from selenium.webdriver.support.ui import WebDriverWait
from selenium.common.exceptions import TimeoutException

logger = logging.getLogger(__name__)
TIMEOUT = 60  # seconds


def __get_pdf_from_html(path, timeout=TIMEOUT, print_options={}):
    browser_options = webdriver.ChromeOptions()
    browser_options.add_argument('headless')
    browser_options.add_argument('disable-gpu')
    browser_options.add_argument('no-sandbox')
    browser_options.add_argument('disable-dev-shm-usage')

    browser = webdriver.Chrome(options=browser_options)

    browser.get(path)

    try:
        WebDriverWait(browser, timeout).until(lambda d: d.execute_script(
            'document.readyState == "complete"'))
    except TimeoutException:
        logger.error(f'Chromium timed out for {path}', exc_info=True)

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


# https://dramatiq.io/guide.html#dead-letters
@dramatiq.actor(queue_name='default', max_retries=3, time_limit=TIMEOUT * 1000)
def generate_pdf(pk):
    from apps.contrib.models import SourcePreview

    source_preview = SourcePreview.objects.get(pk=pk)
    url = source_preview.url
    path = f'{SourcePreview.PREVIEW_FOLDER}/{source_preview.token}.pdf'

    source_preview.status = SourcePreview.PREVIEW_STATUS.IN_PROGRESS
    source_preview.save()

    try:
        pdf_content = __get_pdf_from_html(url)
        source_preview.pdf.save(path, ContentFile(pdf_content))
        source_preview.status = SourcePreview.PREVIEW_STATUS.COMPLETED
    except TimeLimitExceeded:
        logger.error(f'Time limit exceeded for {url}', exc_info=True)
        source_preview.status = SourcePreview.PREVIEW_STATUS.FAILED
        source_preview.remark = 'Took longer than expected'
        source_preview.save()
    except Exception:  # noqa
        logger.error('An exception occurred', exc_info=True)
        source_preview.status = SourcePreview.PREVIEW_STATUS.FAILED
        source_preview.remark = 'Could not generate pdf'
        source_preview.save()

    source_preview.save()
