import logging
from functools import lru_cache
from pathlib import Path

from supabase import Client, create_client

from app.core.config import Settings, get_settings


logger = logging.getLogger("pdf_rag.storage")


class SupabaseStorage:
    def __init__(self, client: Client, bucket: str):
        self.client = client
        self.bucket = bucket

    def build_storage_path(self, user_id: str, document_id: str, filename: str) -> str:
        safe_name = Path(filename).name.replace("\\", "_").replace("/", "_")
        return f"{user_id}/{document_id}/{safe_name}"

    def upload_pdf(self, storage_path: str, pdf_path: str) -> str:
        with open(pdf_path, "rb") as handle:
            pdf_bytes = handle.read()

        self.client.storage.from_(self.bucket).upload(
            path=storage_path,
            file=pdf_bytes,
            file_options={"content-type": "application/pdf", "upsert": "true"},
        )
        logger.info("storage_upload bucket=%s path=%s bytes=%s", self.bucket, storage_path, len(pdf_bytes))
        return storage_path

    def delete_pdf(self, storage_path: str | None) -> None:
        if not storage_path:
            return
        self.client.storage.from_(self.bucket).remove([storage_path])
        logger.info("storage_delete bucket=%s path=%s", self.bucket, storage_path)


@lru_cache
def get_storage() -> SupabaseStorage:
    settings = get_settings()
    settings.require_supabase()
    client = create_client(settings.supabase_url, settings.supabase_service_role_key)
    return SupabaseStorage(client, settings.supabase_storage_bucket)
