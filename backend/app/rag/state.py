from typing import TypedDict


class RAGState(TypedDict, total=False):
    question: str
    document_id: str
    user_id: str
    retrieved_chunks: list[dict]
    answer: str
    confidence: float
    grounded: bool
