import json
from functools import lru_cache
from typing import Any

from app.services.supabase_client import SupabaseRepository, get_repository


class SupabaseVectorStore:
    def __init__(self, repository: SupabaseRepository):
        self.repository = repository

    def upsert_chunks(
        self,
        document_id: str,
        user_id: str,
        chunks: list[dict[str, Any]],
        embeddings: list[list[float]],
    ) -> None:
        rows = []
        for chunk, embedding in zip(chunks, embeddings, strict=True):
            rows.append(
                {
                    "document_id": document_id,
                    "user_id": user_id,
                    "page_number": chunk["page"],
                    "chunk_index": chunk["chunk_index"],
                    "content": chunk["text"],
                    "embedding": json.dumps(embedding),
                }
            )

        for start in range(0, len(rows), 100):
            self.repository.insert_document_chunks(rows[start : start + 100])

    def query(
        self,
        document_id: str,
        user_id: str,
        embedding: list[float],
        top_k: int,
    ) -> list[dict[str, Any]]:
        return self.repository.match_document_chunks(
            document_id=document_id,
            user_id=user_id,
            query_embedding=json.dumps(embedding),
            match_count=top_k,
        )


@lru_cache
def get_vector_store() -> SupabaseVectorStore:
    return SupabaseVectorStore(get_repository())
