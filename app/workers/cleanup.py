from __future__ import annotations

from datetime import datetime, timedelta, timezone
from time import perf_counter

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.core.config import get_settings
from app.db.session import SessionLocal
from app.models import Creation, CreationStatus, GenerationJob, GenerationStatus
from app.observability import (
    clear_request_context,
    configure_logging,
    configure_sentry,
    emit_metrics,
    get_logger,
    set_request_context,
)
from app.observability.metrics import MetricValue
from app.services.storage import AssetStore

configure_logging()
configure_sentry()
logger = get_logger("giftgen.worker.cleanup")


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
    set_request_context(f"cleanup:{datetime.now(timezone.utc).isoformat()}")
    started_at = perf_counter()
    try:
        result = run_cleanup()
        duration_ms = (perf_counter() - started_at) * 1000
        emit_metrics(
            [
                MetricValue(name="CleanupRunCount", value=1),
                MetricValue(name="CleanupDurationMs", value=duration_ms, unit="Milliseconds"),
                MetricValue(name="CleanupExpiredJobs", value=result["expired_jobs"]),
                MetricValue(name="CleanupDeletedCreations", value=result["deleted_creations"]),
                MetricValue(name="CleanupDeletedAssets", value=result["deleted_assets"]),
            ],
            dimensions={"Outcome": "succeeded"},
        )
        logger.info("cleanup_completed", extra={**result, "duration_ms": round(duration_ms, 2)})
        print(result)
    except Exception:
        duration_ms = (perf_counter() - started_at) * 1000
        emit_metrics(
            [
                MetricValue(name="CleanupRunCount", value=1),
                MetricValue(name="CleanupDurationMs", value=duration_ms, unit="Milliseconds"),
            ],
            dimensions={"Outcome": "failed"},
        )
        logger.exception("cleanup_failed", extra={"duration_ms": round(duration_ms, 2)})
        raise
    finally:
        clear_request_context()


if __name__ == "__main__":
    main()
