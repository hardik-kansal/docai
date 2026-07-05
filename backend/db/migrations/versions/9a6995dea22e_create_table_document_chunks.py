"""create_table_document,chunks

Revision ID: 9a6995dea22e
Revises: 62f12763d900
Create Date: 2026-07-04 14:53:21.714575

"""

from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = "9a6995dea22e"
down_revision: Union[str, Sequence[str], None] = "62f12763d900"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("""

    CREATE EXTENSION IF NOT EXISTS "pgcrypto";  -- for gen_random_uuid() 

    CREATE TABLE documents (
        id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        user_id         UUID NOT NULL REFERENCES users(user_id),
        s3_key          TEXT NOT NULL,
        filename        TEXT NOT NULL,
        content_hash    TEXT NOT NULL,           -- sha256 of uploaded bytes, dedupes re-uploads
        status          TEXT NOT NULL DEFAULT 'uploaded',
                        -- uploaded -> parsing -> chunked -> embedding -> indexed -> ready | failed
        docling_doc_uri TEXT,                    -- s3 path to exported DoclingDocument JSON
        embedding_model TEXT,                    -- pinned per document, not global
        embedding_dim   INT,
        error           TEXT,
        created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
        updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
    );
    CREATE UNIQUE INDEX ux_documents_user_hash ON documents(user_id, content_hash);

CREATE TABLE chunks (
    id                   UUID PRIMARY KEY,   -- deterministic, see below — same value used as Qdrant point id
    document_id          UUID NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    chunk_index          INT NOT NULL,
    text                 TEXT NOT NULL,      -- raw chunk.text
    contextualized_text  TEXT NOT NULL,      -- chunker.contextualize(chunk) — what actually gets embedded
    token_count          INT NOT NULL,
    headings             TEXT[],
    page_numbers         INT[],
    content_hash         TEXT NOT NULL,      -- sha256(contextualized_text) — skip re-embedding unchanged chunks
    status               TEXT NOT NULL DEFAULT 'pending_embedding',
    embedded_at          TIMESTAMPTZ,
    indexed_at           TIMESTAMPTZ,
    created_at           TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX ix_chunks_document_id ON chunks(document_id);
CREATE INDEX ix_chunks_pending ON chunks(status) WHERE status <> 'indexed';
    
          
    """)
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
