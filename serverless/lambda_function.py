try:
    pass
except ImportError:
    pass
import os

import boto3
import pdfkit

client = boto3.client('s3')
S3_BUCKET_NAME = os.environ.get('S3_BUCKET_NAME', 'togglecorp-helix')


def handle(event, context):
    url = event.get('url', 'https://google.com')
    filename = event.get('filename', 'test.pdf')

    config = pdfkit.configuration(wkhtmltopdf='/opt/bin/wkhtmltopdf')
    pdf_content = pdfkit.from_url(url, False, configuration=config)
    client.put_object(
        ACL='public-read',
        Body=pdf_content,
        ContentType='application/pdf',
        Bucket=S3_BUCKET_NAME,
        Key='source/previews/' + filename
    )

    object_url = 'https://{0}.s3.amazonaws.com/{1}'.format(S3_BUCKET_NAME, filename)

    response = {
        'statusCode': 200,
        'body': object_url,
        's3_bucket': S3_BUCKET_NAME
    }
    return response
