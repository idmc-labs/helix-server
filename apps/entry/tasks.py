import dramatiq
from django.core.files.base import ContentFile

import base64

from selenium import webdriver
from selenium.webdriver.support.ui import WebDriverWait
from selenium.common.exceptions import TimeoutException


def __get_pdf_from_html(path, timeout=60, print_options={}):
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
        pass

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


@dramatiq.actor
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
    except Exception as e:
        source_preview.status = SourcePreview.PREVIEW_STATUS.FAILED
        source_preview.remark = 'Could not generate pdf'
        raise e

    source_preview.save()
