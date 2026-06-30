import logging

# from typing import Generator
from typing import Final
from .dependencies import get_boto3_client

# from botocore.exceptions import ClientError, BotoCoreError
import magic
from ..config import settings
from ..models.document import PresignedURLResponse
import hmac
import hashlib
import secrets

logger = logging.getLogger(__name__)
settings = settings()


MINIO_WEBHOOK_SECRET = settings.minio_secret_key
_ALLOWED_MIME_TYPES: Final[frozenset[str]] = frozenset(
    {
        "application/pdf",
    }
)


def validate_mime_type(raw_bytes: bytes, object_key):
    # header is stored mostly in first 512 bytes
    # mime=true returns image/jpg instead of image file or jpg file
    detected: str = magic.from_buffer(raw_bytes[:512], mime=True)
    if detected not in _ALLOWED_MIME_TYPES:
        raise ValueError(
            f"Rejected file key={object_key!r}: "
            f"detected MIME={detected!r}, allowed={_ALLOWED_MIME_TYPES}"
        )
    logger.info("MIME validated: %s key=%s", detected, object_key)


def _verify_minio_hmac(body_bytes: bytes, received_sig: str | None) -> None:
    if received_sig is None:
        raise ValueError("x_minio_sig is none")

    expected_sig = hmac.new(
        key=MINIO_WEBHOOK_SECRET.encode(),
        msg=body_bytes,
        digestmod=hashlib.sha256,
    ).hexdigest()

    # secrets.compare_digest prevents timing attacks
    if not secrets.compare_digest(expected_sig, received_sig):
        raise ValueError("signature not matched")
    # "zebra" Fails on 1st letter. Python stops instantly. (Takes 1.0ms)
    # "april" Matches 'a', 'p'. Fails on 'r'.              (Takes 1.2ms)
    # by this attacker can know pwd


def generate_presigned_put_url(
    object_key: str,
    content_type: str,
    file_size_bytes: int,
) -> PresignedURLResponse:
    if file_size_bytes > settings.max_file_size_bytes:
        raise ValueError(
            f"File size {file_size_bytes} exceeds limit {settings.max_file_size_bytes}"
        )
    url = get_boto3_client().generate_presigned_url(
        ClientMethod="put_object",  # means uploading a file
        Params={
            "Bucket": settings.minio_bucket,
            "Key": object_key,
            "ContentType": content_type,
        },
        ExpiresIn=settings.presigned_url_expiry_seconds,
    )
    # generates signature by hashing using sha256
    return PresignedURLResponse(
        upload_url=url,
        object_key=object_key,
        expires_in=settings.presigned_url_expiry_seconds,
    )


"""
def stream_object_bytes(
    bucket: str,
    key: str,
    byte_start: int,
    byte_end: int,
) -> bytes:

    range_header = f"bytes={byte_start}-{byte_end}"
    try:
        response = get_boto3_client().get_object(
            Bucket=bucket,
            Key=key,
            Range=range_header,
        )
        # StreamingBody — read only what was requested
        return response["Body"].read()
    except ClientError as exc:
        error_code = exc.response["Error"]["Code"]
        logger.error(
            "Range request failed key=%s range=%s code=%s",
            key, range_header, error_code,
        )
        raise


def stream_full_object(
    bucket: str,
    key: str,
    chunk_size: int = settings.stream_chunk_size_bytes,
) -> Generator[bytes, None, None]:
    
    try:
        response = get_boto3_client().get_object(Bucket=bucket, Key=key)
        body = response["Body"]
         # returns a  streaming body, with few staring bytes in buffer
         # not string
         # which is roughly socket+ http parser+ small receive buffer

        # if chunk empty stops pulling
        # while true, chunk =body.read(size) if not chunk break
        while chunk := body.read(chunk_size):
            #  tells streaming body to get more bytes
            #  and read once could get chunk size

            yield chunk
    except (ClientError, BotoCoreError) as exc:
        logger.exception("Failed to stream object key=%s: %s", key, exc)
        raise

# head_object method
def get_object_size(bucket: str, key: str) -> int:
    try:
        meta = get_boto3_client().head_object(Bucket=bucket, Key=key)
        return meta["ContentLength"]
    except ClientError as exc:
        logger.error("head_object failed key=%s: %s", key, exc)
        raise

"""
