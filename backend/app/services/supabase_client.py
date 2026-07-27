from functools import lru_cache
from typing import Any
from uuid import uuid4

from supabase import Client, create_client

from app.core.config import get_settings


class NotFoundError(Exception):
    pass


class SupabaseRepository:
    def __init__(self, client: Client):
        self.client = client

    def create_document(self, user_id: str, filename: str) -> dict[str, Any]:
        document_id = str(uuid4())
        payload = {
            "id": document_id,
            "user_id": user_id,
            "filename": filename,
            "status": "processing",
            "page_count": 0,
        }
        response = self.client.table("documents").insert(payload).execute()
        return response.data[0]

    def list_documents(self, user_id: str) -> list[dict[str, Any]]:
        response = (
            self.client.table("documents")
            .select("*")
            .eq("user_id", user_id)
            .order("created_at", desc=True)
            .execute()
        )
        return response.data or []

    def document_to_out(self, document: dict[str, Any], user_id: str) -> dict[str, Any]:
        chunk_count = self.count_document_chunks(str(document["id"]), user_id)
        return {**document, "chunk_count": chunk_count}

    def get_document(self, document_id: str, user_id: str) -> dict[str, Any]:
        response = (
            self.client.table("documents")
            .select("*")
            .eq("id", document_id)
            .eq("user_id", user_id)
            .limit(1)
            .execute()
        )
        if not response.data:
            raise NotFoundError("Document not found")
        return response.data[0]

    def update_document(self, document_id: str, **fields: Any) -> dict[str, Any]:
        response = (
            self.client.table("documents")
            .update(fields)
            .eq("id", document_id)
            .execute()
        )
        return response.data[0] if response.data else {}

    def delete_document(self, document_id: str, user_id: str) -> None:
        self.get_document(document_id, user_id)
        (
            self.client.table("documents")
            .delete()
            .eq("id", document_id)
            .eq("user_id", user_id)
            .execute()
        )

    def insert_document_chunks(self, rows: list[dict[str, Any]]) -> None:
        if rows:
            self.client.table("document_chunks").insert(rows).execute()

    def delete_document_chunks(self, document_id: str, user_id: str) -> None:
        (
            self.client.table("document_chunks")
            .delete()
            .eq("document_id", document_id)
            .eq("user_id", user_id)
            .execute()
        )

    def count_document_chunks(self, document_id: str, user_id: str) -> int:
        response = (
            self.client.table("document_chunks")
            .select("id", count="exact")
            .eq("document_id", document_id)
            .eq("user_id", user_id)
            .execute()
        )
        return response.count or 0

    def match_document_chunks(
        self,
        document_id: str,
        user_id: str,
        query_embedding: str,
        match_count: int,
    ) -> list[dict[str, Any]]:
        response = self.client.rpc(
            "match_document_chunks",
            {
                "target_document_id": document_id,
                "requesting_user_id": user_id,
                "query_embedding": query_embedding,
                "match_count": match_count,
            },
        ).execute()
        rows = response.data or []
        return [
            {
                "text": row.get("content", ""),
                "page": int(row.get("page_number", 0)),
                "score": float(row.get("score", 0.0)),
            }
            for row in rows
        ]

    def create_chat_session(self, user_id: str, document_id: str, title: str) -> dict[str, Any]:
        payload = {
            "user_id": user_id,
            "document_id": document_id,
            "title": title[:80] or "New Chat",
        }
        response = self.client.table("chat_sessions").insert(payload).execute()
        return response.data[0]

    def get_chat_session(self, session_id: str, user_id: str) -> dict[str, Any]:
        response = (
            self.client.table("chat_sessions")
            .select("*")
            .eq("id", session_id)
            .eq("user_id", user_id)
            .limit(1)
            .execute()
        )
        if not response.data:
            raise NotFoundError("Chat session not found")
        return response.data[0]

    def insert_message(
        self,
        session_id: str,
        role: str,
        content: str,
        retrieved_chunks: list[dict[str, Any]] | None = None,
        confidence: float | None = None,
        grounded: bool | None = True,
    ) -> dict[str, Any]:
        payload = {
            "session_id": session_id,
            "role": role,
            "content": content,
            "retrieved_chunks": retrieved_chunks or [],
            "confidence": confidence,
            "grounded": grounded,
        }
        response = self.client.table("messages").insert(payload).execute()
        return response.data[0]

    def get_messages(self, session_id: str, user_id: str) -> list[dict[str, Any]]:
        self.get_chat_session(session_id, user_id)
        response = (
            self.client.table("messages")
            .select("*")
            .eq("session_id", session_id)
            .order("created_at")
            .execute()
        )
        return response.data or []


@lru_cache
def get_repository() -> SupabaseRepository:
    settings = get_settings()
    settings.require_supabase()
    client = create_client(settings.supabase_url, settings.supabase_service_role_key)
    return SupabaseRepository(client)
