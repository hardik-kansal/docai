from fastembed import SparseTextEmbedding
from qdrant_client import models
from qdrant_client.models import ScoredPoint
from ..ingestion.dependencies import get_embedModel, get_vectorPool
from ..config import settings
from ..auth.dependencies import User
from .dependencies import get_reranker
from ..dependencies import call_with_retry
import asyncio
from starlette.concurrency import run_in_threadpool

bm25 = SparseTextEmbedding(model_name="Qdrant/bm25")


def sparse_vector(text: str) -> models.SparseVector:
    emb = next(bm25.embed([text]))
    return models.SparseVector(indices=emb.indices.tolist(), values=emb.values.tolist())


def build_tenant_filter(user: User, document_ids: list[str] | None) -> models.Filter:
    must = [
        models.FieldCondition(
            key="user_id",
            match=models.MatchValue(value=user.user_id),
        )
    ]

    if document_ids:
        must.append(
            models.FieldCondition(
                key="document_id",
                match=models.MatchAny(any=document_ids),
            )
        )

    return models.Filter(must=must)


def embed_query(query: str) -> list[float]:
    return next(get_embedModel().embed([query])).tolist()


async def hybrid_search(
    query_text: str, user: User, document_ids: list[str] | None = None, top_k: int = 40
):
    return await call_with_retry(
        get_vectorPool().query_points,
        budget_s=10,
        collection_name=settings().COLLECTION,
        # runs independently means top 100 for dense, top 100 for sparse
        prefetch=[
            models.Prefetch(query=embed_query(query_text), using="dense", limit=100),
            models.Prefetch(query=sparse_vector(query_text), using="sparse", limit=100),
        ],
        query=models.FusionQuery(fusion=models.Fusion.RRF),
        query_filter=build_tenant_filter(user, document_ids),
        limit=top_k,
    )


# Elasticsearch / OpenSearch bm25 is much better though, can be run locally
# raw bm25 is ram, cpu expensive, not scalable, doesnt save


async def rerank_results(
    query: str,
    hits: list[ScoredPoint],
    top_n: int = 10,
    budget_ms: int = 250,
) -> list[tuple[float, ScoredPoint]]:
    docs = [hit.payload["text"][:1000] for hit in hits]
    # req truncation till model max tokens(query + top chunks)
    # tokenizer inside already trucates but better to do manually
    try:
        # req since it takes time, every other req have to wait then
        scores = await asyncio.wait_for(
            run_in_threadpool(get_reranker().rerank, query, docs),
            timeout=budget_ms / 1000,
        )
    except asyncio.TimeoutError:
        # fall back to just topn rather than failing the request
        return [(hit.score, hit) for hit in hits[:top_n]]

    ranked = sorted(zip(hits, scores), key=lambda x: x[1], reverse=True)
    return [(score, hit) for hit, score in ranked[:top_n]]
