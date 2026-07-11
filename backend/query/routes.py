import logging
from typing import Annotated

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from fastapi.responses import StreamingResponse
from ..auth.dependencies import get_current_user, User
from .services import ans_query

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/query")


class QueryRequest(BaseModel):
    query: str = Field(
        ..., min_length=1, max_length=2048, description="Natural-language question"
    )
    document_ids: list[str] | None = Field(
        default=None,
        description="Scope retrieval to these document IDs. Omit to search all user docs.",
    )


class QueryResponse(BaseModel):
    answer: str
    sources: list[dict]  # will be typed properly once retrieval layer is wired


"""
results.points
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
) -> StreamingResponse:
    return StreamingResponse(
        ans_query(payload.query, user, payload.document_ids),
        media_type="text/event-stream",
    )
