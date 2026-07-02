from docling_core.transforms.chunker import HybridChunker
from docling.document_converter import DocumentConverter
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


def get_boto3_client() -> boto3.client:
    assert _s3_client is not None, "_s3_client not initialized"
    return _s3_client


_converter: DocumentConverter | None = None


def get_converter() -> DocumentConverter:
    assert _converter is not None, "_converter not init"
    return _converter


def set_converter(converter: DocumentConverter):
    global _converter
    _converter = converter


_chunker: HybridChunker | None = None


def get_chunker() -> HybridChunker:
    assert _chunker is not None, "_chunker not init"
    return _chunker


def set_chunker(chunker: HybridChunker):
    global _chunker
    _chunker = chunker
