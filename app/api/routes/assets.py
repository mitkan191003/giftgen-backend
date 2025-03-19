from pathlib import Path

import boto3
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse, RedirectResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.config import get_settings
from app.db.session import get_db
from app.models import Asset, Creation, Share, User

router = APIRouter()


def _serve_asset(asset: Asset):
    settings = get_settings()
    if asset.storage_bucket == "local":
        path = Path(asset.storage_key)
        if not path.exists():
            raise HTTPException(status_code=404, detail="Asset file not found")
        return FileResponse(path=path, media_type=asset.mime_type, filename=path.name)

    client = boto3.client("s3", region_name=settings.aws_region)
    url = client.generate_presigned_url(
        "get_object",
        Params={"Bucket": asset.storage_bucket, "Key": asset.storage_key},
        ExpiresIn=3600,
    )
    return RedirectResponse(url=url, status_code=307)


@router.get("/assets/{asset_id}/content")
def get_asset_content(
    asset_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    asset = db.scalar(
        select(Asset)
        .join(Asset.creation)
        .where(Asset.id == asset_id, Creation.user_id == current_user.id)
    )
    if asset is None:
        raise HTTPException(status_code=404, detail="Asset not found")

    return _serve_asset(asset)


@router.get("/public/assets/{asset_id}")
def get_public_asset_content(asset_id: str, db: Session = Depends(get_db)):
    asset = db.scalar(
        select(Asset)
        .join(Asset.creation)
        .join(Creation.shares)
        .where(Asset.id == asset_id, Share.is_active.is_(True))
    )
    if asset is None:
        raise HTTPException(status_code=404, detail="Asset not found")

    return _serve_asset(asset)
