from google.genai._gaos.types.interactions.interaction import Interaction
from fastembed import SparseTextEmbedding
from qdrant_client import models
from qdrant_client.models import ScoredPoint
from ..ingestion.dependencies import get_embedModel, get_vectorPool
from ..config import settings
from ..auth.dependencies import User
from .dependencies import get_reranker, get_llm
from ..dependencies import call_with_retry
import asyncio
from starlette.concurrency import run_in_threadpool
import logging
from ..models.llm_ouput import GroundedAnswer, AbstainReason, AbstainOutput, Citation

logger = logging.getLogger(__name__)

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
    try:
        return await call_with_retry(
            get_vectorPool().query_points,
            budget_s=10,
            collection_name=settings().COLLECTION,
            # runs independently means top 100 for dense, top 100 for sparse
            prefetch=[
                models.Prefetch(
                    query=embed_query(query_text), using="dense", limit=100
                ),
                models.Prefetch(
                    query=sparse_vector(query_text), using="sparse", limit=100
                ),
            ],
            query=models.FusionQuery(fusion=models.Fusion.RRF),
            query_filter=build_tenant_filter(user, document_ids),
            limit=top_k,
        )
    except Exception:
        logger.exception("cannot retrieve chunks")
        return None


# Elasticsearch / OpenSearch bm25 is much better though, can be run locally
# raw bm25 is ram, cpu expensive, not scalable, doesnt save


async def rerank_results(
    query: str,
    points: list[ScoredPoint],
    top_n: int = 10,
    budget_ms: int = 250,
) -> list[tuple[float, ScoredPoint]]:
    docs = [point.payload["text"][:1000] for point in points]
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
        return [(point.score, point) for point in points[:top_n]]

    ranked = sorted(zip(points, scores), key=lambda x: x[1], reverse=True)
    return [(score, point) for point, score in ranked[:top_n]]


async def ans_query(query_text: str, user: User) -> GroundedAnswer | None:
    results = await hybrid_search(
        query_text=query_text,
        user=user,
    )
    if results is None:
        return GroundedAnswer(
            answer=AbstainOutput.INPUT_REJECTED,
            citations=[],
            confidence=0.0,
            abstained=True,
            abstain_reason=AbstainReason.INPUT_REJECTED,
        )
    # cross encoder
    reranked = await rerank_results(
        query=query_text,
        points=results.points,
        top_n=10,
    )
    context = [
        {
            "chunk_id": point.payload["chunk_index"],
            "contextualized_text": point.payload["contextualized_text"],
        }
        for _, point in reranked
    ]

    llmResponse = await call_llm(query_text, context)
    if llmResponse is None:
        return GroundedAnswer(
            answer=AbstainOutput.GENERATION_UNAVAILABLE,
            citations=[
                Citation(chunk_id=str(c["chunk_id"]), quote=c["contextualized_text"])
                for c in context
            ],
            confidence=0.0,
            abstained=True,
            abstain_reason=AbstainReason.GENERATION_UNAVAILABLE,
        )
    if llmResponse.status == "completed":
        return GroundedAnswer.model_validate_json(llmResponse.output_text)


async def call_llm(query_text: str, context: list[dict]) -> Interaction:
    ctx_block = "\n\n".join(
        f"""Chunk ID: {c["chunk_id"]}
    Chunk Contextualized Text:
    {c["contextualized_text"]}"""
        for c in context
    )

    input_text = f"""Context:
    {ctx_block}

    Question:
    {query_text}"""

    # stream,
    # store chats-> response and request for later retrieval.
    try:
        interaction = get_llm().interactions.create(
            model="gemini-3.5-flash",
            input=input_text,
            system_instruction=settings().system_prompt,
            response_format={
                "type": "text",
                "mime_type": "application/json",
                "schema": GroundedAnswer.model_json_schema(),
            },
        )
        return interaction
    except Exception:
        logger.exception("LLM generation failed")
        return None


# # Server-side state (recommended)
# interaction1 = client.interactions.create(
#     model="gemini-3.5-flash",
#     input="I have 2 dogs in my house.",
# )
# print("Response 1:", interaction1.output_text)

# interaction2 = client.interactions.create(
#     model="gemini-3.5-flash",
#     input="How many paws are in my house?",
#     previous_interaction_id=interaction1.id,
# )
# print("Response 2:", interaction2.output_text)
