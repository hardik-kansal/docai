from pydantic import BaseModel, Field
from enum import StrEnum


class Citation(BaseModel):
    chunk_id: str
    quote: str  # short excerpt from that chunk supporting the claim


class AbstainReason(StrEnum):
    NONE = "none"
    INPUT_REJECTED = "input_rejected"  # injection/moderation blocked the request
    NO_RELEVANT_CONTEXT = "no_relevant_context"  # retrieval found nothing usable
    GENERATION_UNAVAILABLE = (
        "generation_unavailable"  # circuit open / LLM down — degraded fallback
    )
    LOW_GROUNDEDNESS = "low_groundedness"  # HHEM self-check failed


class GroundedAnswer(BaseModel):
    answer: str
    citations: list[Citation]
    confidence: float = Field(ge=0.0, le=1.0)
    abstained: bool
    abstain_reason: AbstainReason = AbstainReason.NONE


class AbstainOutput(StrEnum):
    INPUT_REJECTED = "input_rejected"
    NO_RELEVANT_CONTEXT = """
    Could not retrieve chunks at the moment..
    """
    GENERATION_UNAVAILABLE = """
    llm generation failed here it is req chunks
    """
