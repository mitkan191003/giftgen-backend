from __future__ import annotations

import argparse
import shutil
from dataclasses import dataclass
from pathlib import Path

import boto3
from sqlalchemy import func
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.core.config import get_settings
from app.db.session import SessionLocal
from app.models import Asset
from app.models import Creation
from app.models import GenerationJob
from app.models import Share


S3_CREATIONS_PREFIX = "creations/"


@dataclass(slots=True)
class DeletionSummary:
    creations: int
    jobs: int
    assets: int
    shares: int
    deleted_storage_objects: int


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Wipe generated gift data from the dev database and asset storage."
    )
    parser.add_argument(
        "--yes",
        action="store_true",
        help="Actually perform the wipe. Without this flag, the script exits without deleting anything.",
    )
    return parser.parse_args()


def _assert_safe_dev_target() -> None:
    settings = get_settings()

    if settings.environment != "development":
        raise SystemExit(
            "Refusing to wipe data because ENVIRONMENT is not 'development'. "
            f"Resolved value: {settings.environment!r}"
        )

    dev_markers = [
        settings.asset_bucket_name,
        settings.database_endpoint or "",
        settings.database_secret_id or "",
        settings.public_share_base_url,
    ]
    if not any("giftgen-dev" in marker or "dev.giftgen" in marker for marker in dev_markers):
        raise SystemExit(
            "Refusing to wipe data because the resolved storage/database targets do not look like dev. "
            f"Resolved markers: {dev_markers}"
        )


def _count_existing_rows() -> DeletionSummary:
    with SessionLocal() as db:
        return DeletionSummary(
            creations=db.scalar(select(func.count()).select_from(Creation)) or 0,
            jobs=db.scalar(select(func.count()).select_from(GenerationJob)) or 0,
            assets=db.scalar(select(func.count()).select_from(Asset)) or 0,
            shares=db.scalar(select(func.count()).select_from(Share)) or 0,
            deleted_storage_objects=0,
        )


def _delete_creation_rows() -> None:
    with SessionLocal() as db:
        creations = list(
            db.scalars(
                select(Creation)
                .options(selectinload(Creation.assets))
                .order_by(Creation.created_at)
            )
        )
        for creation in creations:
            db.delete(creation)
        db.commit()


def _delete_s3_prefix(bucket: str, prefix: str, region: str) -> int:
    client = boto3.client("s3", region_name=region)
    paginator = client.get_paginator("list_objects_v2")
    deleted = 0

    for page in paginator.paginate(Bucket=bucket, Prefix=prefix):
        objects = [{"Key": item["Key"]} for item in page.get("Contents", [])]
        if not objects:
            continue
        deleted += len(objects)
        for start in range(0, len(objects), 1000):
            client.delete_objects(
                Bucket=bucket,
                Delete={"Objects": objects[start : start + 1000], "Quiet": True},
            )

    return deleted


def _delete_local_assets(root: str) -> int:
    target = Path(root) / "creations"
    if not target.exists():
        return 0

    deleted = sum(1 for path in target.rglob("*") if path.is_file())
    shutil.rmtree(target)
    return deleted


def run_wipe() -> DeletionSummary:
    settings = get_settings()
    before = _count_existing_rows()

    _delete_creation_rows()

    if settings.asset_storage_mode == "s3":
        deleted_storage_objects = _delete_s3_prefix(
            bucket=settings.asset_bucket_name,
            prefix=S3_CREATIONS_PREFIX,
            region=settings.aws_region,
        )
    else:
        deleted_storage_objects = _delete_local_assets(settings.local_asset_root)

    return DeletionSummary(
        creations=before.creations,
        jobs=before.jobs,
        assets=before.assets,
        shares=before.shares,
        deleted_storage_objects=deleted_storage_objects,
    )


def main() -> int:
    args = _parse_args()
    _assert_safe_dev_target()

    settings = get_settings()
    print(
        "Resolved dev wipe target:",
        {
            "environment": settings.environment,
            "database_endpoint": settings.database_endpoint,
            "database_secret_id": settings.database_secret_id,
            "asset_storage_mode": settings.asset_storage_mode,
            "asset_bucket_name": settings.asset_bucket_name,
        },
    )

    if not args.yes:
        print("Refusing to wipe dev data without --yes.")
        return 1

    result = run_wipe()
    print(
        {
            "deleted_creations": result.creations,
            "deleted_jobs": result.jobs,
            "deleted_asset_rows": result.assets,
            "deleted_shares": result.shares,
            "deleted_storage_objects": result.deleted_storage_objects,
        }
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
