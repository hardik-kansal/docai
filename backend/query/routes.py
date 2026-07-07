import logging
from typing import Annotated

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from ..auth.dependencies import get_current_user, User
from .services import hybrid_search, rerank_results

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/query")


class QueryRequest(BaseModel):
    query: str = Field(
        ..., min_length=1, max_length=2048, description="Natural-language question"
    )


class QueryResponse(BaseModel):
    answer: str
    sources: list[dict]  # will be typed properly once retrieval layer is wired


"""
points=[
    ScoredPoint(
        id='uuid5(documet :idx)', 
        version=8, 
        score=0.5, 
        payload={
            'chunk_index': 1, 
            'contextualized_text': "...",
            'headings': [], 
            'page_numbers': [1], 
            'text': '...', 
            'user_id': '9c6d70626e8c4fbe993c0d2e679eaa68'
            }, 
            vector=None, 
            shard_key=None, 
            order_value=None), 
    ScoredPoint(...)
]
"""


@router.post("/")
async def query(
    payload: QueryRequest,
    user: Annotated[User, Depends(get_current_user)],
) -> QueryResponse:
    results = await hybrid_search(
        query_text=payload.query,
        user=user,
    )
    reranked = await rerank_results(
        query=payload.query,
        hits=results.points,  # top 40 from RRF fusion
        top_n=10,
    )
    sources = [
        {
            "chunk_id": str(hit.id),
            "retrieval_score": hit.score,  # original RRF score
            "rerank_score": rerank_score,  # cross-encoder score
            **hit.payload,
        }
        for rerank_score, hit in reranked
    ]
    return QueryResponse(answer="", sources=sources)
