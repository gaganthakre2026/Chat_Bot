from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


BACKEND_DIR = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    app_name: str = "PDF-Grounded RAG Chatbot"
    environment: str = "local"
    api_prefix: str = ""

    supabase_url: str = ""
    supabase_anon_key: str = ""
    supabase_service_role_key: str = ""

    llm_provider: str = "gemini"

    openai_api_key: str = ""
    openai_chat_model: str = "gpt-4o-mini"
    openai_embedding_model: str = "text-embedding-3-large"

    gemini_api_key: str = ""
    gemini_chat_model: str = "gemini-3.6-flash"
    gemini_embedding_model: str = "gemini-embedding-2"
    gemini_embedding_dimensions: int = 1536

    rag_top_k: int = 6
    rag_similarity_threshold: float = 0.55
    chunk_size_chars: int = 3000
    chunk_overlap_chars: int = 450
    upload_max_mb: int = 20
    supabase_storage_bucket: str = "documents"

    cors_origins: str = "http://localhost:5173"

    model_config = SettingsConfigDict(
        env_file=BACKEND_DIR / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    def require_supabase(self) -> None:
        missing = [
            name
            for name, value in {
                "SUPABASE_URL": self.supabase_url,
                "SUPABASE_ANON_KEY": self.supabase_anon_key,
                "SUPABASE_SERVICE_ROLE_KEY": self.supabase_service_role_key,
            }.items()
            if not value
        ]
        if missing:
            raise RuntimeError(f"Missing Supabase configuration: {', '.join(missing)}")

    def require_rag(self) -> None:
        self.require_llm_provider()

    def require_openai(self) -> None:
        missing = [
            name
            for name, value in {"OPENAI_API_KEY": self.openai_api_key}.items()
            if not value
        ]
        if missing:
            raise RuntimeError(f"Missing OpenAI configuration: {', '.join(missing)}")

    def require_gemini(self) -> None:
        missing = [
            name
            for name, value in {"GEMINI_API_KEY": self.gemini_api_key}.items()
            if not value
        ]
        if missing:
            raise RuntimeError(f"Missing Gemini configuration: {', '.join(missing)}")

    def require_llm_provider(self) -> None:
        provider = self.llm_provider.lower()
        if provider == "openai":
            self.require_openai()
            return
        if provider == "gemini":
            self.require_gemini()
            return
        raise RuntimeError(f"Unsupported LLM_PROVIDER: {self.llm_provider}")


@lru_cache
def get_settings() -> Settings:
    return Settings()
