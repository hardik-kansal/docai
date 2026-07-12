import logging

# from typing import Generator
from typing import Final
from .dependencies import get_boto3_client

# from botocore.exceptions import ClientError, BotoCoreError
import magic
from ..config import settings
from ..models.document import PresignedURLResponse

logger = logging.getLogger(__name__)
settings = settings()


MINIO_WEBHOOK_SECRET = settings.minio_secret_key
_ALLOWED_MIME_TYPES: Final[frozenset[str]] = frozenset(
    {
        "application/pdf",
    }
)


def validate_mime_type(raw_bytes: bytes, object_key):
    # for pdf we need roughly 5 bytes though
    # mime=true returns image/jpg instead of "image file or jpg file"
    detected: str = magic.from_buffer(raw_bytes[:512], mime=True)
    if detected not in _ALLOWED_MIME_TYPES:
        raise ValueError(
            f"Rejected file key={object_key!r}: "
            f"detected MIME={detected!r}, allowed={_ALLOWED_MIME_TYPES}"
        )
    logger.info("MIME validated: %s key=%s", detected, object_key)


def generate_presigned_post_url(
    object_key: str, max_bytes: int
) -> PresignedURLResponse:
    presigned_url = get_boto3_client().generate_presigned_post(
        Bucket=settings.minio_bucket,
        Key=object_key,
        Conditions=[
            # key must match else attacker could upload at any location
            # possibly overwrite anyones document.
            {"key": object_key},
            # File size: 1 byte to max_bytes
            ["content-length-range", 1, max_bytes],
            # Must upload as PDF, though s3 only checks through header
            ["eq", "$Content-Type", "application/pdf"],
            # Store as private, (default)
            # means s3 wont allow anyone access it publicly even user who submitted it
            # only admin
            {"acl": "private"},
        ],
        # adds these fields in presigned_url json, so user must send all these
        # else upload req would fail
        Fields={
            "key": object_key,
            "Content-Type": "application/pdf",
            "acl": "private",
        },
        ExpiresIn=settings.presigned_url_expiry_seconds,
    )
    logger.debug(presigned_url)

    return PresignedURLResponse(
        upload_url=presigned_url["url"],  # actual MinIO POST endpoint
        upload_fields=presigned_url["fields"],  # auth fields that must be in the form
        object_key=object_key,
        expires_in=settings.presigned_url_expiry_seconds,
    )


VIEW_URL_EXPIRY_SECONDS = 15 * 60  # 15 minutes


def generate_presigned_get_url(object_key: str) -> str:
    """Return a time-limited GET URL for a private S3/MinIO object.

    Unlike generate_presigned_post_url (which returns a url + fields dict for
    multipart form upload), generate_presigned_url("get_object") returns a
    single plain URL the browser can open directly — no form, no extra headers.
    Response-Content-Disposition tells the browser to display inline (PDF viewer)
    rather than force-download.
    """
    return get_boto3_client().generate_presigned_url(
        "get_object",
        Params={
            "Bucket": settings.minio_bucket,
            "Key": object_key,
            "ResponseContentType": "application/pdf",
            "ResponseContentDisposition": "inline",
        },
        ExpiresIn=VIEW_URL_EXPIRY_SECONDS,
    )


"""
presigned_url json
{
'url': 'http://localhost:9000/contracts', 
'fields': { 
            'key': 'uploads/ab0b00856e464dd1965bea5ffd3aaaf5/9ebcd527-f4c5-4325-8296-67b9b065c242/hardik', 
            'Content-Type': 'application/pdf',
            'acl': 'private',
            'x-amz-server-side-encryption': 'AES256', 
            'AWSAccessKeyId': 'hardik',
            'policy': '...long str, 
            'signature': 'hrf2vLs9Juro4mVVjCapDuW3H2k='
            }
}

"""


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
