from pathlib import Path
from typing import Iterator

import boto3
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse, StreamingResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.config import get_settings
from app.db.session import get_db
from app.models import Asset, Creation, Share, User

router = APIRouter()


def _iter_s3_body(body) -> Iterator[bytes]:
    try:
        while chunk := body.read(1024 * 1024):
            yield chunk
    finally:
        body.close()


def _serve_asset(asset: Asset):
    settings = get_settings()
    if asset.storage_bucket == "local":
        path = Path(asset.storage_key)
        if not path.exists():
            raise HTTPException(status_code=404, detail="Asset file not found")
        return FileResponse(path=path, media_type=asset.mime_type, filename=path.name)

    client = boto3.client("s3", region_name=settings.aws_region)
    response = client.get_object(
        Bucket=asset.storage_bucket,
        Key=asset.storage_key,
    )
    headers = {
        "Content-Length": str(response.get("ContentLength", asset.file_size)),
        "Cache-Control": "private, max-age=3600",
    }

    if response.get("ETag"):
        headers["ETag"] = str(response["ETag"]).strip('"')

    return StreamingResponse(
        _iter_s3_body(response["Body"]),
        media_type=asset.mime_type,
        headers=headers,
    )


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
