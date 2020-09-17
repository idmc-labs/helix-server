try:
    import unzip_requirements
except ImportError:
    pass
import os
from subprocess import call
import sys

# import boto3


def handle(event, context):
    url = event.get('url', 'https://google.com')

    import pdfkit
    config = pdfkit.configuration(wkhtmltopdf='binary/wkhtmltopdf')
    try:
        pdf_content = pdfkit.from_url(url, False, configuration=config)
    except Exception as e:
        print(e)
        response = {
            "statusCode": 500,
            "body": 'Unable to generate pdf.'
        }
        return response

    # s3 = boto3.client('s3')
    # s3.upload_fileobj(pdf_content,
    #                   os.environ.get('S3_BUCKET_NAME'),
    #                   event['file_name'])

    response = {
        "statusCode": 200,
        "body": pdf_content
    }

    return response
