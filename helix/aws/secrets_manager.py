import boto3
from botocore.exceptions import ClientError
import json
import logging

logger = logging.getLogger(__name__)


def fetch_db_credentials_from_secret_arn(cluster_secret_arn):
    logger.warning(f'Fetching db cluster secret using ARN: {cluster_secret_arn}')

    # the passed secret is the aws arn instead
    session = boto3.session.Session()
    client = session.client(
        service_name='secretsmanager',
        # region_name='us-east-1',
    )

    try:
        get_secret_value_response = client.get_secret_value(SecretId=cluster_secret_arn)
    except ClientError as e:
        logger.error(f"Got client error {e.response['Error']['Code']} for {cluster_secret_arn}")
    else:
        logger.info('Found secret...')
        # Secrets Manager decrypts the secret value using the associated KMS CMK
        # Depending on whether the secret was a string or binary, only one of these fields will be populated
        if 'SecretString' in get_secret_value_response:
            text_secret_data = get_secret_value_response['SecretString']
            return json.loads(text_secret_data)
        else:
            # binary_secret_data = get_secret_value_response['SecretBinary']
            logger.error("Secret should be decrypted to string but found binary instead")
    raise Exception('Failed to parse/fetch secret')
