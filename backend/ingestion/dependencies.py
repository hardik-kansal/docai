import boto3
from boto3.s3.transfer import TransferConfig

_s3_client = None

s3_download_config = TransferConfig(
    multipart_threshold=1024
    * 1024
    * 50,  # Starts multi-thread downloading if file > 50MB
    max_concurrency=10,  # Use up to 10 parallel threads
    num_download_attempts=5,  # Retry 5 times before giving up
)


def set_boto3_client(_client: boto3.client):
    global _s3_client
    _s3_client = _client


def get_boto3_client(_client: boto3.client) -> boto3.client:
    assert _s3_client is not None, "_s3_client not initialized"
    return _s3_client
