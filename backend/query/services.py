from aiobreaker import CircuitBreakerError
from fastembed import SparseTextEmbedding
from qdrant_client import models
from qdrant_client.models import ScoredPoint
from ..ingestion.dependencies import get_embedModel, get_vectorPool
from ..config import settings
from ..auth.dependencies import User
from .dependencies import get_reranker, get_llm, GroundedJsonException
from ..dependencies import call_with_retry, get_circuit_breaker
import asyncio
from starlette.concurrency import run_in_threadpool
import logging
from ..models.llm_ouput import GroundedAnswer, AbstainReason, AbstainOutput, Citation
from ..guardrail.llmGuard import classify
import json

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
    docs = [point.payload.get("text", "")[:1000] for point in points]
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


async def ans_query(
    query_text: str, user: User, document_ids: list[str] | None = None
) -> GroundedAnswer | None:
    if await query_unsafe(query_text):
        raise GroundedJsonException(grounded_answer=get_unsafe_response())
    results = await hybrid_search(
        query_text=query_text,
        user=user,
        document_ids=document_ids,
    )
    if results is None:
        raise GroundedJsonException(
            grounded_answer=GroundedAnswer(
                answer=AbstainOutput.NO_RELEVANT_CONTEXT,
                citations=[],
                confidence=0.0,
                abstained=True,
                abstain_reason=AbstainReason.NO_RELEVANT_CONTEXT,
            )
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
    for _, point in reranked:
        if await query_unsafe(point.payload["contextualized_text"]):
            raise GroundedJsonException(
                GroundedAnswer(
                    answer=AbstainOutput.INPUT_REJECTED,
                    citations=[],
                    confidence=0.0,
                    abstained=True,
                    abstain_reason=AbstainReason.INPUT_REJECTED,
                )
            )
    try:
        llmResponse = await call_llm(query_text, context)
    except CircuitBreakerError:
        logger.warning("gemini circuit breaker opened")
        llmResponse = None
    if llmResponse is None:
        raise GroundedJsonException(
            GroundedAnswer(
                answer=AbstainOutput.GENERATION_UNAVAILABLE,
                citations=[
                    Citation(
                        chunk_id=str(c["chunk_id"]), quote=c["contextualized_text"]
                    )
                    for c in context
                ],
                confidence=0.0,
                abstained=True,
                abstain_reason=AbstainReason.GENERATION_UNAVAILABLE,
            )
        )

    accumulated_thoughts = ""
    accumulated_json_tokens = ""

    try:
        for event in llmResponse:
            if event.event_type == "interaction.created":
                yield f"data: {json.dumps({'type': 'started'}, default=str)}\n\n"
            elif event.event_type == "step.delta":
                if event.delta.type == "thought_summary":
                    text_chunk = event.delta.content.text
                    accumulated_thoughts += text_chunk
                    yield f"data: {json.dumps({'type': 'thought', 'content': text_chunk})}\n\n"

                elif event.delta.type == "text" and event.delta.text:
                    text_chunk = event.delta.text
                    accumulated_json_tokens += text_chunk
                    yield f"data: {json.dumps({'type': 'structured_json_data', 'content': text_chunk})}\n\n"
            elif event.event_type == "interaction.completed":
                usage = event.interaction.usage
                yield f"data: {
                    json.dumps(
                        {
                            'type': 'usage',
                            'content': {
                                'input_tokens': usage.total_input_tokens,
                                'output_tokens': usage.total_output_tokens,
                                'thought_tokens': usage.total_thought_tokens,
                                'total_tokens': usage.total_tokens,
                            },
                        }
                    )
                }\n\n"

        # if accumulated_json_tokens:
        #     try:
        #         parsed_response = json.loads(accumulated_json_tokens)
        #         hhem_score = await HHEMValidator.evaluate_factual_consistency(
        #             source_text=source_documents_text,
        #             generated_text=parsed_response.get("answer", "")
        #         )
        #         yield f"data: {json.dumps({'type': 'hhem_verification', 'score': hhem_score, 'status': 'passed' if hhem_score >= 0.5 else 'failed'})}\n\n"
        #     except json.JSONDecodeError:
        #         logger.error("Failed downstream parsing step for streaming string compilation.")

    except Exception:
        logger.exception(
            "Active execution failure intercepted during live session stream."
        )
        yield f"data: {json.dumps({'type': 'error', 'content': 'Upstream link severed mid-session.'})}\n\n"


# opens circuit breaker if 5 diff req returns error here
@get_circuit_breaker()
async def call_llm(query_text: str, context: list[dict]):
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
        # have default timeout, retry logic api side
        stream = get_llm().interactions.create(
            model=settings().GEMINI_MODEL,
            input=input_text,
            system_instruction=settings().system_prompt,
            response_format={
                "type": "text",
                "mime_type": "application/json",
                "schema": GroundedAnswer.model_json_schema(),
            },
            generation_config={"thinking_summaries": "auto", "thinking_level": "high"},
            stream=True,
        )
        return stream
    except Exception:
        logger.exception("LLM generation failed")
        raise


def get_unsafe_response() -> GroundedAnswer:
    return GroundedAnswer(
        answer=AbstainOutput.INPUT_REJECTED,
        citations=[],
        confidence=0.0,
        abstained=True,
        abstain_reason=AbstainReason.INPUT_REJECTED,
    )


async def query_unsafe(query_txt: str, budget_ms: int = 1000) -> bool:
    try:
        result = await asyncio.wait_for(
            run_in_threadpool(classify, query_txt),
            timeout=budget_ms / 1000,
        )
        return result["is_unsafe"]
    except asyncio.TimeoutError:
        logger.warning(
            "query_unsafe timed out after %dms, treating as unsafe", budget_ms
        )
        return True


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


"""
====== Interaction structure =========

status='completed'
model='gemini-3.5-flash'
agent=None 
id='v1_...' 
created='2026-07-08T12:28:25Z'
updated='2026-07-08T12:28:25Z'
system_instruction=None
tools=None
usage=Usage(
   total_input_tokens=1250,
   input_tokens_by_modality=[ModalityTokens(modality='text', tokens=1250)], total_cached_tokens=0,
   cached_tokens_by_modality=None,
   total_output_tokens=150,
   output_tokens_by_modality=None,
   total_tool_use_tokens=0,
   tool_use_tokens_by_modality=None,
   total_thought_tokens=217,
   total_tokens=1617,
   grounding_tool_count=None)
response_modalities=None
response_mime_type=None
previous_interaction_id=None
environment_id=None
service_tier='standard'
webhook_config=None
steps=[
   ThoughtStep(type='thought', signature='...', summary=None),
   ModelOutputStep(
       type='model_output',
       content=[
           TextContent(
               text='{
                   \n  "answer": "During training, label smoothing of value \\u0335_ls = 0.1 was employed. Although this hurts perplexity because the model learns to be more unsure, it improves both accuracy and the BLEU score.",\n 
                   "citations": [\n   
                       {\n     
                       "chunk_id": "1",\n     
                       "quote": "Label Smoothing During training, we employed label smoothing of value ϵ ls = 0 . 1 [36]. This hurts perplexity, as the model learns to be more unsure, but improves accuracy and BLEU score."\n
                       }\n 
                           ],\n 
                   "confidence": 1.0,\n 
                   "abstained": false\n
                       }',
               type='text',
               annotations=None
               )
               ],
       error=None)
   ]
response_format=None
environment=None
generation_config=None
cached_content=None
agent_config=None
input=None
output_text='{\n 
   "answer": "During training, label smoothing of value \\u0335_ls = 0.1 was employed. Although this hurts perplexity because the model learns to be more unsure, it improves both accuracy and the BLEU score.",\n 
   "citations": [\n   
                   {\n     
                       "chunk_id": "1",\n     
                       "quote": "Label Smoothing During training, we employed label smoothing of value ϵ ls = 0 . 1 [36]. This hurts perplexity, as the model learns to be more unsure, but improves accuracy and BLEU score."\n  
                   }\n
               ],\n
 "confidence": 1.0,\n
  "abstained": false\n
  }'
output_image=None
output_audio=None
output_video=None
object='interaction'

"""


"""
event.interaction object
InteractionSseEventInteraction(
    id='v1_...', 
    status='completed', 
    object='interaction', 
    model='gemini-3.1-flash-lite', 
    agent=None, 
    created='2026-07-11T14:30:32Z', 
    updated='2026-07-11T14:30:32Z', 
    service_tier='standard', 
    usage=Usage(
        total_input_tokens=1250, 
        input_tokens_by_modality=
        [ModalityTokens(modality='text', tokens=1250)], 
        total_cached_tokens=0, 
        cached_tokens_by_modality=None, 
        total_output_tokens=152, 
        output_tokens_by_modality=None, 
        total_tool_use_tokens=0, 
        tool_use_tokens_by_modality=None, 
        total_thought_tokens=867, 
        total_tokens=2269, 
        grounding_tool_count=None), steps=None) 
    event_type='interaction.completed' 
    event_id=None 
    metadata=None
"""
