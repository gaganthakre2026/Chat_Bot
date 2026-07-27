import logging
import os

import fitz
from langchain_text_splitters import RecursiveCharacterTextSplitter

from app.core.config import get_settings
from app.services.llm_provider import get_llm_provider
from app.services.supabase_vector_store import get_vector_store
from app.services.supabase_client import get_repository


logger = logging.getLogger("pdf_rag.ingestion")

EMBED_BATCH_SIZE = 32


def embed_chunks_batched(texts: list[str]) -> list[list[float]]:
    provider = get_llm_provider()
    embeddings: list[list[float]] = []
    for start in range(0, len(texts), EMBED_BATCH_SIZE):
        batch = texts[start : start + EMBED_BATCH_SIZE]
        embeddings.extend(provider.embed_texts(batch))
        logger.info(
            "embedding_batch document_progress=%s/%s",
            min(start + len(batch), len(texts)),
            len(texts),
        )
    return embeddings


def extract_pages(pdf_path: str) -> list[dict]:
    pages: list[dict] = []
    with fitz.open(pdf_path) as document:
        for index, page in enumerate(document, start=1):
            text = page.get_text("text").strip()
            pages.append({"page": index, "text": text})
    return pages


def chunk_pages(pages: list[dict]) -> list[dict]:
    settings = get_settings()
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=settings.chunk_size_chars,
        chunk_overlap=settings.chunk_overlap_chars,
        separators=["\n\n", "\n", ". ", " ", ""],
    )

    chunks: list[dict] = []
    for page in pages:
        page_chunks = splitter.split_text(page["text"])
        for chunk_index, text in enumerate(page_chunks):
            cleaned = text.strip()
            if cleaned:
                chunks.append(
                    {
                        "page": page["page"],
                        "chunk_index": chunk_index,
                        "text": cleaned,
                    }
                )
    return chunks


def process_pdf_document(document_id: str, user_id: str, pdf_path: str) -> None:
    repository = get_repository()
    settings = get_settings()
    try:
        settings.require_rag()
        pages = extract_pages(pdf_path)
        chunks = chunk_pages(pages)
        if not chunks:
            raise ValueError("No selectable text was found in the PDF.")

        embeddings = embed_chunks_batched([chunk["text"] for chunk in chunks])
        get_vector_store().upsert_chunks(
            document_id=document_id,
            user_id=user_id,
            chunks=chunks,
            embeddings=embeddings,
        )
        repository.update_document(
            document_id,
            status="ready",
            page_count=len(pages),
            error_message=None,
        )
        logger.info(
            "ingestion_complete document_id=%s user_id=%s pages=%s chunks=%s",
            document_id,
            user_id,
            len(pages),
            len(chunks),
        )
    except Exception as exc:
        logger.exception("ingestion_failed document_id=%s user_id=%s", document_id, user_id)
        repository.update_document(
            document_id,
            status="failed",
            error_message=str(exc)[:1000],
        )
    finally:
        try:
            os.remove(pdf_path)
        except OSError:
            pass
