from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import auth, chat, documents
from app.core.config import get_settings
from app.core.logging import RequestLoggingMiddleware, configure_logging
from app.models.schemas import HealthResponse, RagHealthResponse
from app.rag.langgraph_pipeline import get_rag_pipeline


configure_logging()
settings = get_settings()

app = FastAPI(title=settings.app_name)

app.add_middleware(RequestLoggingMiddleware)

cors_kwargs: dict = {
    "allow_credentials": True,
    "allow_methods": ["*"],
    "allow_headers": ["*"],
    "allow_origins": settings.cors_origin_list,
}
cors_kwargs["allow_origin_regex"] = r"https?://(localhost|127\.0\.0\.1)(:\d+)?|https://.*\.vercel\.app"

app.add_middleware(CORSMiddleware, **cors_kwargs)

app.include_router(documents.router, prefix=settings.api_prefix)
app.include_router(chat.router, prefix=settings.api_prefix)
app.include_router(auth.router, prefix=settings.api_prefix)


@app.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    return HealthResponse(
        status="ok",
        service=settings.app_name,
        environment=settings.environment,
    )


@app.get("/health/rag", response_model=RagHealthResponse)
async def health_rag() -> RagHealthResponse:
    settings.require_rag()
    pipeline = get_rag_pipeline()
    return RagHealthResponse(
        status="ok",
        pipeline="langgraph",
        llm_provider=settings.llm_provider,
        embedding_dimensions=settings.gemini_embedding_dimensions
        if settings.llm_provider.lower() == "gemini"
        else 1536,
        steps=[
            "extract_pdf_text",
            "chunk_text",
            "embed_chunks",
            "store_vectors",
            "retrieve_chunks",
            "grade_relevance",
            "generate_answer",
            "groundedness_check",
        ],
    )
