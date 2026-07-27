import os
import tempfile
from pathlib import Path
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, File, HTTPException, UploadFile, status

from app.core.config import Settings, get_settings
from app.core.security import CurrentUser, get_current_user
from app.models.schemas import DocumentOut, UploadResponse
from app.services.ingestion import process_pdf_document
from app.services.supabase_client import NotFoundError, SupabaseRepository, get_repository
from app.services.supabase_storage import SupabaseStorage, get_storage


router = APIRouter(prefix="/documents", tags=["documents"])


def _validate_pdf(file: UploadFile) -> str:
    filename = Path(file.filename or "document.pdf").name
    if not filename.lower().endswith(".pdf"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only PDF uploads are supported",
        )
    return filename


async def _save_upload_to_temp(file: UploadFile, max_bytes: int) -> str:
    handle = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf")
    temp_path = handle.name
    bytes_written = 0
    try:
        with handle:
            while chunk := await file.read(1024 * 1024):
                bytes_written += len(chunk)
                if bytes_written > max_bytes:
                    raise HTTPException(
                        status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                        detail="PDF exceeds the configured upload size limit",
                    )
                handle.write(chunk)
        return temp_path
    except Exception:
        try:
            os.remove(temp_path)
        except OSError:
            pass
        raise


@router.post("/upload", response_model=UploadResponse, status_code=status.HTTP_202_ACCEPTED)
async def upload_document(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    user: CurrentUser = Depends(get_current_user),
    settings: Settings = Depends(get_settings),
    repository: SupabaseRepository = Depends(get_repository),
    storage: SupabaseStorage = Depends(get_storage),
) -> UploadResponse:
    filename = _validate_pdf(file)
    temp_path = await _save_upload_to_temp(
        file,
        max_bytes=settings.upload_max_mb * 1024 * 1024,
    )
    document = repository.create_document(user.id, filename)
    document_id = str(document["id"])
    storage_path = storage.build_storage_path(user.id, document_id, filename)

    try:
        storage.upload_pdf(storage_path, temp_path)
        try:
            document = repository.update_document(
                document_id,
                storage_path=storage_path,
            )
        except Exception:
            document = {**document, "storage_path": storage_path}
    except Exception as exc:
        repository.update_document(
            document_id,
            status="failed",
            error_message=f"Failed to store PDF in Supabase Storage: {exc}"[:1000],
        )
        try:
            os.remove(temp_path)
        except OSError:
            pass
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Failed to store PDF in Supabase Storage. Ensure the documents bucket exists (run migrations/003_storage.sql).",
        ) from exc

    background_tasks.add_task(
        process_pdf_document,
        document_id,
        user.id,
        temp_path,
    )
    return UploadResponse(document=DocumentOut.model_validate(document))


@router.get("", response_model=list[DocumentOut])
async def list_documents(
    user: CurrentUser = Depends(get_current_user),
    repository: SupabaseRepository = Depends(get_repository),
) -> list[DocumentOut]:
    documents = repository.list_documents(user.id)
    return [
        DocumentOut.model_validate(repository.document_to_out(document, user.id))
        for document in documents
    ]


@router.get("/{document_id}", response_model=DocumentOut)
async def get_document(
    document_id: UUID,
    user: CurrentUser = Depends(get_current_user),
    repository: SupabaseRepository = Depends(get_repository),
) -> DocumentOut:
    try:
        document = repository.get_document(str(document_id), user.id)
    except NotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return DocumentOut.model_validate(repository.document_to_out(document, user.id))


@router.delete("/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_document(
    document_id: UUID,
    user: CurrentUser = Depends(get_current_user),
    repository: SupabaseRepository = Depends(get_repository),
    storage: SupabaseStorage = Depends(get_storage),
) -> None:
    try:
        document = repository.get_document(str(document_id), user.id)
    except NotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc

    storage_path = document.get("storage_path") or storage.build_storage_path(
        user.id,
        str(document_id),
        document["filename"],
    )

    repository.delete_document_chunks(str(document_id), user.id)
    repository.delete_document(str(document_id), user.id)
    try:
        storage.delete_pdf(storage_path)
    except Exception:
        pass
