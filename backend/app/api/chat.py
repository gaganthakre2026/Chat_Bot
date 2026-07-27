from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status

from app.core.security import CurrentUser, get_current_user
from app.models.schemas import ChatMessageIn, ChatResponse, MessageOut, RetrievedChunk
from app.rag.langgraph_pipeline import get_rag_pipeline
from app.services.supabase_client import NotFoundError, SupabaseRepository, get_repository


router = APIRouter(prefix="/chat", tags=["chat"])


@router.post("/{document_id}/message", response_model=ChatResponse)
async def send_message(
    document_id: UUID,
    payload: ChatMessageIn,
    user: CurrentUser = Depends(get_current_user),
    repository: SupabaseRepository = Depends(get_repository),
) -> ChatResponse:
    try:
        document = repository.get_document(str(document_id), user.id)
    except NotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc

    if document["status"] != "ready":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Document is {document['status']}; wait until it is ready before chatting.",
        )

    chunk_count = repository.count_document_chunks(str(document_id), user.id)
    if chunk_count == 0:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This document has no indexed chunks yet. Re-upload the PDF and wait until indexing completes.",
        )

    try:
        pipeline = get_rag_pipeline()
    except RuntimeError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc

    if payload.session_id:
        try:
            session = repository.get_chat_session(str(payload.session_id), user.id)
        except NotFoundError as exc:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
        if session["document_id"] != str(document_id):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Chat session belongs to a different document",
            )
    else:
        session = repository.create_chat_session(
            user_id=user.id,
            document_id=str(document_id),
            title=payload.question,
        )

    repository.insert_message(
        session_id=session["id"],
        role="user",
        content=payload.question,
    )

    result = pipeline.run(payload.question, str(document_id), user.id)
    retrieved_chunks = [
        {
            "text": chunk.get("text", ""),
            "page": int(chunk.get("page", 0)),
            "score": float(chunk.get("score", 0.0)),
        }
        for chunk in result.get("retrieved_chunks", [])
    ]
    repository.insert_message(
        session_id=session["id"],
        role="assistant",
        content=result["answer"],
        retrieved_chunks=retrieved_chunks,
        confidence=float(result["confidence"]),
        grounded=bool(result["grounded"]),
    )

    return ChatResponse(
        answer=result["answer"],
        confidence=float(result["confidence"]),
        retrieved_chunks=[RetrievedChunk.model_validate(chunk) for chunk in retrieved_chunks],
        grounded=bool(result["grounded"]),
        session_id=session["id"],
    )


@router.get("/{session_id}/history", response_model=list[MessageOut])
async def get_history(
    session_id: UUID,
    user: CurrentUser = Depends(get_current_user),
    repository: SupabaseRepository = Depends(get_repository),
) -> list[MessageOut]:
    try:
        messages = repository.get_messages(str(session_id), user.id)
    except NotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return [MessageOut.model_validate(message) for message in messages]
