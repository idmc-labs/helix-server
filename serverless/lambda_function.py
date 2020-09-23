try:
    import unzip_requirements
except ImportError:
    pass
import os
from subprocess import call
import sys
import logging
import boto3

logger = logging.getLogger(__name__)
client = boto3.client('s3')
S3_BUCKET_NAME = 'togglecorp-helix'


def handle(event, context):
    url = event.get('url', 'https://google.com')
    filename = event.get('filename', 'test.pdf')

    import pdfkit
    config = pdfkit.configuration(wkhtmltopdf='/opt/bin/wkhtmltopdf')
    try:
        pdf_content = pdfkit.from_url(url, False, configuration=config)
    except Exception as e:
        logger.exception(e)
        response = {
            'statusCode': 500,
            'body': 'Unable to generate pdf.'
        }
        return response
    try:
        client.put_object(
            ACL='public-read',
            Body=pdf_content,
            ContentType='application/pdf',
            Bucket=S3_BUCKET_NAME,
            Key=filename
        )
    except Exception as e:
        logger.exception(e)
        response = {
            'statusCode': 500,
            'body': 'Unable to create object into s3.'
        }
        return response

    object_url = 'https://{0}.s3.amazonaws.com/{1}'.format(S3_BUCKET_NAME, filename)

    response = {
        'statusCode': 200,
        'body': object_url
    }

    return response
