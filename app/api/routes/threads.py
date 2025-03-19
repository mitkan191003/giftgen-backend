from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models import ChatMessage, ChatThread, ConversationRole, User
from app.schemas import (
    ChatMessageCreate,
    ChatMessageRead,
    MessageExchangeRead,
    ThreadCreate,
    ThreadDetail,
    ThreadRead,
)
from app.services.guardrails import PromptGuardrailService
from app.services.prompting import PromptRefiner

router = APIRouter()


@router.post("", response_model=ThreadRead)
def create_thread(
    payload: ThreadCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ChatThread:
    thread = ChatThread(user_id=current_user.id, title=payload.title)
    db.add(thread)
    db.commit()
    db.refresh(thread)
    return thread


@router.get("", response_model=list[ThreadRead])
def list_threads(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[ChatThread]:
    statement = (
        select(ChatThread)
        .where(ChatThread.user_id == current_user.id)
        .order_by(ChatThread.updated_at.desc())
    )
    return list(db.scalars(statement))


@router.get("/{thread_id}", response_model=ThreadDetail)
def get_thread(
    thread_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ChatThread:
    thread = db.scalar(
        select(ChatThread)
        .options(selectinload(ChatThread.messages))
        .where(ChatThread.id == thread_id, ChatThread.user_id == current_user.id)
    )
    if thread is None:
        raise HTTPException(status_code=404, detail="Thread not found")
    return thread


@router.post("/{thread_id}/messages", response_model=MessageExchangeRead)
def create_message(
    thread_id: str,
    payload: ChatMessageCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> MessageExchangeRead:
    thread = db.scalar(select(ChatThread).where(ChatThread.id == thread_id, ChatThread.user_id == current_user.id))
    if thread is None:
        raise HTTPException(status_code=404, detail="Thread not found")

    guardrail = PromptGuardrailService().inspect(payload.content)
    if not guardrail.allowed:
        raise HTTPException(
            status_code=400,
            detail={"message": "Prompt rejected by guardrails", "reasons": guardrail.reasons},
        )

    if not thread.title:
        thread.title = guardrail.normalized_text[:72]

    user_message = ChatMessage(
        thread_id=thread.id,
        role=ConversationRole.user.value,
        content=guardrail.normalized_text,
        metadata_json={"guardrail_reasons": []},
    )
    refinement = PromptRefiner().refine(guardrail.normalized_text)
    assistant_message = ChatMessage(
        thread_id=thread.id,
        role=ConversationRole.assistant.value,
        content=refinement.assistant_reply,
        metadata_json={"structured_prompt": refinement.structured_prompt},
    )

    db.add(user_message)
    db.add(assistant_message)
    db.commit()
    db.refresh(user_message)
    db.refresh(assistant_message)
    db.refresh(thread)

    return MessageExchangeRead(
        user_message=ChatMessageRead.model_validate(user_message),
        assistant_message=ChatMessageRead.model_validate(assistant_message),
        suggested_prompt=refinement.structured_prompt,
    )
