from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.api.deps import get_current_user
from app.core.config import get_settings
from app.db.session import get_db
from app.models import ChatThread, Creation, CreationStatus, GenerationJob, GenerationStatus, User
from app.schemas import AssetRead, CreationCreate, CreationEnvelope, CreationRead, GenerationJobRead
from app.services.guardrails import PromptGuardrailService

router = APIRouter()
settings = get_settings()


@router.post("/creations", response_model=CreationEnvelope)
def create_creation(
    payload: CreationCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> CreationEnvelope:
    guardrail = PromptGuardrailService().inspect(payload.prompt)
    if not guardrail.allowed:
        raise HTTPException(
            status_code=400,
            detail={"message": "Prompt rejected by guardrails", "reasons": guardrail.reasons},
        )

    source_thread = None
    if payload.source_thread_id:
        source_thread = db.scalar(
            select(ChatThread).where(
                ChatThread.id == payload.source_thread_id,
                ChatThread.user_id == current_user.id,
            )
        )
        if source_thread is None:
            raise HTTPException(status_code=404, detail="Thread not found")
        source_thread.updated_at = datetime.now(timezone.utc)

    creation = Creation(
        user_id=current_user.id,
        source_thread_id=payload.source_thread_id,
        title=payload.title,
        final_prompt=guardrail.normalized_text,
        status=CreationStatus.queued.value,
        visibility=payload.visibility.value,
    )
    job = GenerationJob(
        creation=creation,
        status=GenerationStatus.queued.value,
        input_payload={"prompt": guardrail.normalized_text},
    )
    db.add(creation)
    db.add(job)
    db.commit()
    db.refresh(creation)
    db.refresh(job)

    return CreationEnvelope(
        creation=CreationRead.model_validate(creation),
        job=GenerationJobRead.model_validate(job),
    )


@router.get("/creations", response_model=list[CreationRead])
def list_creations(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[CreationRead]:
    statement = (
        select(Creation)
        .options(selectinload(Creation.assets))
        .where(Creation.user_id == current_user.id)
        .order_by(Creation.updated_at.desc())
    )
    creations = list(db.scalars(statement))
    now = datetime.now(timezone.utc)
    for creation in creations:
        creation.last_accessed_at = now
    db.commit()
    return [
        CreationRead.model_validate(
            {
                **creation.__dict__,
                "assets": [
                    AssetRead.model_validate(
                        {
                            **asset.__dict__,
                            "download_url": f"{settings.api_v1_prefix}/assets/{asset.id}/content",
                        }
                    )
                    for asset in creation.assets
                ],
            }
        )
        for creation in creations
    ]


@router.get("/jobs/{job_id}", response_model=GenerationJobRead)
def get_job(
    job_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> GenerationJob:
    statement = (
        select(GenerationJob)
        .join(GenerationJob.creation)
        .where(GenerationJob.id == job_id, Creation.user_id == current_user.id)
    )
    job = db.scalar(statement)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    return job
