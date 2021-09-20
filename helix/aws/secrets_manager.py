import boto3
from botocore.exceptions import ClientError
import json
import logging
import os

logger = logging.getLogger(__name__)


def get_db_cluster_secret():
    cluster_secret = os.environ.get('HELIXDBCLUSTER_SECRET')
    try:
        return json.loads(cluster_secret)
    except json.decoder.JSONDecodeError:
        logger.info(f'Getting db cluster secret using ARN: {cluster_secret}')

    # the passed secret is the aws arn instead
    session = boto3.session.Session()
    client = session.client(
        service_name='secretsmanager',
        # region_name='us-east-1',
    )

    try:
        get_secret_value_response = client.get_secret_value(
            SecretId=cluster_secret
        )
    except ClientError as e:
        logger.info('Got client error')
        if e.response['Error']['Code'] == 'ResourceNotFoundException':
            logger.error("The requested secret " + cluster_secret + " was not found")
            logger.info("The requested secret " + cluster_secret + " was not found")
        elif e.response['Error']['Code'] == 'InvalidRequestException':
            logger.error("The request was invalid due to:", e)
            logger.info("The request was invalid due to:", e)
        elif e.response['Error']['Code'] == 'InvalidParameterException':
            logger.error("The request had invalid params:", e)
            logger.info("The request had invalid params:", e)
        elif e.response['Error']['Code'] == 'DecryptionFailure':
            logger.error("The requested secret can't be decrypted using the provided KMS key:", e)
            logger.info("The requested secret can't be decrypted using the provided KMS key:", e)
        else:
            logger.error("An error occurred on service side:", e)
            logger.info("An error occurred on service side:", e)
    else:
        logger.info('Found secret...')
        # Secrets Manager decrypts the secret value using the associated KMS CMK
        # Depending on whether the secret was a string or binary, only one of these fields will be populated
        if 'SecretString' in get_secret_value_response:
            text_secret_data = get_secret_value_response['SecretString']
            return json.loads(text_secret_data)
        else:
            # binary_secret_data = get_secret_value_response['SecretBinary']
            logger.error("Secret should be encrypted as string but found binary")
    return {}
