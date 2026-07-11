from docling_core.transforms.chunker import BaseChunk, HybridChunker
import uuid
from .repository import DocRepository, Chunk
from ..models.document import DocumentRow
import hashlib
from dataclasses import astuple
import logging


NAMESPACE = uuid.UUID("6f2a9e1e-2b3a-4c8b-9e3a-7a6f1c9d5e10")
BATCH_SIZE = 10
logger = logging.getLogger(__name__)


class DocService:
    def __init__(self, repo: DocRepository) -> None:
        self._repo = repo

    def create_record_row(
        self, idx: int, chunk: BaseChunk, chunker: HybridChunker, document_id: uuid.UUID
    ):
        contextualized = chunker.contextualize(chunk)
        page_numbers = sorted(
            {prov.page_no for item in chunk.meta.doc_items for prov in item.prov}
        )

        """
        chunks -
                text
                meta -  
                    docMeta -
                            docItems per para
                    captions
                    headings
                    origin 
        """

        return astuple(
            Chunk(
                id=uuid.uuid5(NAMESPACE, f"{document_id}:{idx}"),
                document_id=document_id,
                chunk_index=idx,
                text=chunk.text,
                contextualized_text=contextualized,
                token_count=chunker.tokenizer.count_tokens(contextualized),
                headings=chunk.meta.headings or [],
                page_numbers=page_numbers,
                content_hash=hashlib.sha256(contextualized.encode("utf-8")).hexdigest(),
            )
        )

    async def register_document(
        self,
        user_id: str,
        s3_key: str,
        filename: str,
        content_hash: str,
        docling_doc_uri: str,
        embedding_model: str,
        embedding_dim: int,
        error: str | None = None,
    ) -> uuid.UUID:
        document_id = await self._repo.create_document(
            user_id=uuid.UUID(user_id),
            s3_key=s3_key,
            filename=filename,
            content_hash=content_hash,
            docling_doc_uri=docling_doc_uri,
            embedding_model=embedding_model,
            embedding_dim=embedding_dim,
            error=error if error else "",
        )

        return document_id

    async def check_document(self, user_id: str, content_hash: str) -> bool:
        return await self._repo.check_document_exists(
            user_id=uuid.UUID(user_id),
            content_hash=content_hash,
        )

    async def list_documents(self, user_id: str) -> list[DocumentRow]:
        return await self._repo.list_documents(uuid.UUID(user_id))

    async def get_s3_key(self, document_id: str, user_id: str) -> str | None:
        return await self._repo.get_s3_key(uuid.UUID(document_id), uuid.UUID(user_id))
