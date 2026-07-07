from __future__ import annotations
import datetime
import asyncpg
import uuid
from dataclasses import dataclass


@dataclass(slots=True)
class Chunk:
    id: uuid.UUID
    document_id: uuid.UUID
    chunk_index: int
    text: str
    contextualized_text: str
    token_count: int
    headings: list[str]
    page_numbers: list[int]
    content_hash: str
    status: str = "pending_embedding"
    embedded_at: datetime.timezone | None = None
    indexed_at: datetime.timezone | None = None
    created_at: datetime.timezone | None = None


class DocRepository:
    """All doc, chunk related sql"""

    def __init__(self, pool: asyncpg.Pool) -> None:
        self._pool = pool

    async def bulk_upsert_chunks(self, rows):
        # rows can be any combo of list, tuple -> like list of tuples

        async with self._pool.acquire() as conn:
            # now all below would run on a single connection session
            # which is req since each connection session have its own staging table
            await conn.execute("TRUNCATE staging_chunks")
            # trucate is quite faster than delete
            # since pg deletes row by row
            # while truncate mean table is labelled as empty

            await conn.copy_records_to_table(
                "staging_chunks",
                records=rows,
                columns=[
                    "id",
                    "document_id",
                    "chunk_index",
                    "text",
                    "contextualized_text",
                    "token_count",
                    "headings",
                    "page_numbers",
                    "content_hash",
                ],
            )

            await conn.execute("""
                    INSERT INTO chunks (
                        id,
                        document_id,
                        chunk_index,
                        text,
                        contextualized_text,
                        token_count,
                        headings,
                        page_numbers,
                        content_hash
                    )
                    SELECT
                        id,
                        document_id,
                        chunk_index,
                        text,
                        contextualized_text,
                        token_count,
                        headings,
                        page_numbers,
                        content_hash
                    FROM staging_chunks
                    ON CONFLICT (id)
                    DO UPDATE SET
                        text = EXCLUDED.text,
                        contextualized_text = EXCLUDED.contextualized_text,
                        token_count = EXCLUDED.token_count,
                        headings = EXCLUDED.headings,
                        page_numbers = EXCLUDED.page_numbers,
                        content_hash = EXCLUDED.content_hash;
                """)  # exluded is just temp table where select rows are stored
            # if anything fails in this await, it rollbacks, but staging already done,
            # which isnt a problem since we truncate

    async def create_document(
        self,
        user_id: uuid.UUID,
        s3_key: str,
        filename: str,
        content_hash: str,
        docling_doc_uri: str,
        embedding_model: str,
        embedding_dim: int,
        error: str,
    ) -> uuid.UUID:
        doc_id = await self._pool.fetchval(
            """
            INSERT INTO documents (
                user_id,
                s3_key,
                filename,
                content_hash,
                docling_doc_uri,                    
                embedding_model,                  
                embedding_dim,
                error
            )
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
            ON CONFLICT (user_id, content_hash) DO NOTHING
            RETURNING id;
            """,
            user_id,
            s3_key,
            filename,
            content_hash,
            docling_doc_uri,
            embedding_model,
            embedding_dim,
            error,
        )
        if doc_id is None:
            return await self._pool.fetchval(
                """
                SELECT id FROM documents 
                WHERE user_id = $1 AND content_hash = $2;
                """,
                user_id,
                content_hash,
            )

        async def check_document_exists(
            self, user_id: uuid.UUID, content_hash: str
        ) -> bool:
            result = await self._pool.fetchval(
                """
                SELECT EXISTS (
                    SELECT 1 FROM documents 
                    WHERE user_id = $1 AND content_hash = $2
                );
                """,
                user_id,
                content_hash,
            )
            return bool(result)


"""
for inserting into pg, there are multiple ways
1. single insert, slowest
2. multi row insert, fast for batch, performance depends machine to machine bz of batch size
3. copy fastest among these, does not parse sql, cant add conditional code
4. copy with merging-
Most time gets into parsing multiple sql, and network time, pg server is fast enough though.
through copy parsing eliminated.
copy millions without any condition into temporary table, then merge this table with main
with conditons.
copy with merging is very fast, took 22min for a job which insert one row took 14hr.

staging table is temp based-> means remains for per one active connection, and avoid WAL,
so pg truncates them in crash

we can also do copy with (merging in batches).


"""
