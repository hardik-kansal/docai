from docling_core.transforms.chunker import HybridChunker
from docling.document_converter import DocumentConverter
import boto3
from boto3.s3.transfer import TransferConfig
from .services import DocService
from .repository import DocRepository
import asyncpg

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


_pool: asyncpg.Pool | None = None


def set_asyncpg_pool(pool: asyncpg.Pool):
    global _pool
    _pool = pool


def get_asyncpg_pool() -> asyncpg.Pool:
    assert _pool is not None, "Postgres pool not initialized"
    return _pool


async def init_pg_connection(conn: asyncpg.Connection):
    await conn.execute("""
        CREATE TEMP TABLE staging_chunks (
            id UUID,
            document_id UUID,
            chunk_index INTEGER,
            text TEXT,
            contextualized_text TEXT,
            token_count INTEGER,
            headings TEXT[],
            page_numbers INTEGER[],
            content_hash TEXT
        ) ON COMMIT PRESERVE ROWS;  
    """)


# async pool client creates connection pool,
# each connection pool on init creates this table once
# also since this is temp, no need to add overhead with constraints
# if something wrong automatically, when copying into actual table, error would occur.


def get_DocService() -> DocService:
    return DocService(DocRepository(get_asyncpg_pool()))
