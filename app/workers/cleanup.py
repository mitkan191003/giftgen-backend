from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.core.config import get_settings
from app.db.session import SessionLocal
from app.models import Creation, CreationStatus, GenerationJob, GenerationStatus
from app.services.storage import AssetStore


def run_cleanup() -> dict[str, int]:
    settings = get_settings()
    cutoff = datetime.now(timezone.utc) - timedelta(days=settings.cleanup_retention_days)

    expired_jobs = 0
    deleted_creations = 0
    deleted_assets = 0

    with SessionLocal() as db:
        stale_jobs = list(
            db.scalars(
                select(GenerationJob)
                .options(selectinload(GenerationJob.creation))
                .where(
                    GenerationJob.status.in_(
                        [GenerationStatus.queued.value, GenerationStatus.running.value]
                    ),
                    GenerationJob.created_at < cutoff,
                )
            )
        )

        for job in stale_jobs:
            job.status = GenerationStatus.expired.value
            job.completed_at = datetime.now(timezone.utc)
            job.error_message = "Expired by scheduled cleanup"
            if job.creation.status in {
                CreationStatus.draft.value,
                CreationStatus.queued.value,
                CreationStatus.running.value,
            }:
                job.creation.status = CreationStatus.failed.value
            expired_jobs += 1

        stale_creations = list(
            db.scalars(
                select(Creation)
                .options(selectinload(Creation.assets))
                .where(
                    Creation.status.in_(
                        [CreationStatus.failed.value, CreationStatus.deleted.value]
                    ),
                    Creation.updated_at < cutoff,
                )
            )
        )

        store = AssetStore()
        for creation in stale_creations:
            for asset in creation.assets:
                store.delete(asset.storage_bucket, asset.storage_key)
                deleted_assets += 1
            db.delete(creation)
            deleted_creations += 1

        db.commit()

    return {
        "expired_jobs": expired_jobs,
        "deleted_creations": deleted_creations,
        "deleted_assets": deleted_assets,
    }


def main() -> None:
    result = run_cleanup()
    print(result)


if __name__ == "__main__":
    main()
