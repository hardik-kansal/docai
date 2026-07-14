from pydantic import BaseModel, Field
from enum import StrEnum


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
    confidence: float = Field(ge=0.0, le=1.0)
    abstained: bool
    abstain_reason: AbstainReason = AbstainReason.NONE


class AbstainOutput(StrEnum):
    INPUT_REJECTED = (
        "I cannot fulfill this request as it violates safety or moderation guidelines."
    )
    NO_RELEVANT_CONTEXT = "I could not find any relevant information in the provided documents to answer your question."
    GENERATION_UNAVAILABLE = "I am currently unable to generate a response due to a temporary service issue. Please refer to the retrieved documents in the meantime."
