from fastembed.rerank.cross_encoder import TextCrossEncoder
from google import genai
from ..config import settings


_reranker: TextCrossEncoder | None = None


def get_reranker() -> TextCrossEncoder:
    assert _reranker is not None, "_reranker not initialized"
    return _reranker


def set_reranker(reranker: TextCrossEncoder) -> None:
    global _reranker
    _reranker = reranker


_client = genai.Client(api_key=settings().GEMINI_KEY)


def get_llm() -> genai.Client:
    return _client
