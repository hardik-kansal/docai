from fastembed.rerank.cross_encoder import TextCrossEncoder

_reranker: TextCrossEncoder | None = None


def get_reranker() -> TextCrossEncoder:
    assert _reranker is not None, "_reranker not initialized"
    return _reranker


def set_reranker(reranker: TextCrossEncoder) -> None:
    global _reranker
    _reranker = reranker
