from ..models.llm_ouput import GroundedAnswer
from fastembed.rerank.cross_encoder import TextCrossEncoder
from google import genai


_reranker: TextCrossEncoder | None = None


def get_reranker() -> TextCrossEncoder:
    assert _reranker is not None, "_reranker not initialized"
    return _reranker


def set_reranker(reranker: TextCrossEncoder) -> None:
    global _reranker
    _reranker = reranker


_client: genai.Client | None = None


def get_llm() -> genai.Client:
    assert _client is not None, "_client not initialized"
    return _client


def set_llm(client: genai.Client) -> None:
    global _client
    _client = client


class GroundedJsonException(Exception):
    def __init__(self, grounded_answer: GroundedAnswer, status_code: int = 200):
        self.grounded_answer = grounded_answer
        self.status_code = status_code
