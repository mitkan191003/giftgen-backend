from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.api.deps import get_current_user
from app.core.config import get_settings
from app.db.session import get_db
from app.models import Creation, CreationStatus, Share, ShareType, User, Visibility
from app.schemas import AssetRead, PublicShareRead, ShareCreate, ShareRead
from app.services.shares import generate_share_slug

router = APIRouter()
settings = get_settings()


def _derive_creation_visibility(creation: Creation) -> str:
    active_share_types = {share.share_type for share in creation.shares if share.is_active}
    if ShareType.public.value in active_share_types:
        return Visibility.public.value
    if ShareType.unlisted.value in active_share_types:
        return Visibility.unlisted.value
    return Visibility.private.value


@router.post("/shares", response_model=ShareRead)
def create_share(
    payload: ShareCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ShareRead:
    creation = db.scalar(
        select(Creation)
        .options(selectinload(Creation.assets), selectinload(Creation.shares))
        .where(Creation.id == payload.creation_id, Creation.user_id == current_user.id)
    )
    if creation is None:
        raise HTTPException(status_code=404, detail="Creation not found")
    if creation.status != CreationStatus.ready.value:
        raise HTTPException(status_code=409, detail="Only ready creations can be shared")
    if not creation.assets:
        raise HTTPException(status_code=409, detail="Creation has no assets to share")

    slug = generate_share_slug(creation.title)
    while db.scalar(select(Share).where(Share.share_slug == slug)) is not None:
        slug = generate_share_slug(creation.title)

    share = Share(creation_id=creation.id, share_type=payload.share_type.value, share_slug=slug)

    db.add(share)
    creation.shares.append(share)
    creation.visibility = _derive_creation_visibility(creation)
    db.commit()
    db.refresh(share)

    return ShareRead.model_validate(
        {
            **share.__dict__,
            "public_url": f"{settings.public_share_base_url.rstrip('/')}/{share.share_slug}",
        }
    )


@router.post("/shares/{share_id}/revoke", response_model=ShareRead)
def revoke_share(
    share_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ShareRead:
    share = db.scalar(
        select(Share)
        .options(selectinload(Share.creation).selectinload(Creation.shares))
        .join(Share.creation)
        .where(Share.id == share_id, Creation.user_id == current_user.id)
    )
    if share is None:
        raise HTTPException(status_code=404, detail="Share not found")

    share.is_active = False
    share.revoked_at = datetime.now(timezone.utc)
    share.creation.visibility = _derive_creation_visibility(share.creation)
    db.commit()
    db.refresh(share)

    return ShareRead.model_validate(
        {
            **share.__dict__,
            "public_url": f"{settings.public_share_base_url.rstrip('/')}/{share.share_slug}",
        }
    )


@router.get("/public/shares/{slug}", response_model=PublicShareRead)
def get_public_share(slug: str, db: Session = Depends(get_db)) -> PublicShareRead:
    share = db.scalar(
        select(Share)
        .options(selectinload(Share.creation).selectinload(Creation.assets), selectinload(Share.creation).selectinload(Creation.user))
        .where(Share.share_slug == slug, Share.is_active.is_(True))
    )
    if share is None:
        raise HTTPException(status_code=404, detail="Share not found")

    creation = share.creation
    return PublicShareRead(
        title=creation.title,
        prompt=creation.final_prompt,
        visibility=creation.visibility,
        share_type=share.share_type,
        owner_display_name=creation.user.display_name,
        assets=[
            AssetRead.model_validate(
                {
                    **asset.__dict__,
                    "download_url": f"{settings.api_v1_prefix}/public/assets/{asset.id}",
                }
            )
            for asset in creation.assets
        ],
    )
