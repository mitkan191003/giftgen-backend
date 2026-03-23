from __future__ import annotations

import argparse
import time
from datetime import datetime, timezone
from time import perf_counter

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.db.session import SessionLocal
from app.models import Asset, AssetType, CreationStatus, Creation, GenerationJob, GenerationStatus
from app.observability import (
    clear_request_context,
    configure_logging,
    configure_sentry,
    emit_metrics,
    get_logger,
    set_request_context,
)
from app.observability.metrics import MetricValue
from app.services.modal import ModalGenerationClient
from app.services.storage import AssetStore

configure_logging()
configure_sentry()
logger = get_logger("giftgen.worker.generation")


def process_next_job() -> bool:
    with SessionLocal() as db:
        job = db.scalar(
            select(GenerationJob)
            .options(selectinload(GenerationJob.creation))
            .where(GenerationJob.status == GenerationStatus.queued.value)
            .order_by(GenerationJob.created_at.asc())
        )
        if job is None:
            return False

        set_request_context(f"job:{job.id}")
        creation: Creation = job.creation
        job.status = GenerationStatus.running.value
        job.started_at = datetime.now(timezone.utc)
        creation.status = CreationStatus.running.value
        db.commit()
        started_at = perf_counter()
        queue_age_ms = (job.started_at - job.created_at).total_seconds() * 1000
        emit_metrics(
            [
                MetricValue(name="GenerationStartedCount", value=1),
                MetricValue(name="GenerationQueueAgeMs", value=queue_age_ms, unit="Milliseconds"),
            ],
            dimensions={"Outcome": "started"},
            properties={"creation_id": creation.id, "job_id": job.id},
        )
        logger.info(
            "generation_started",
            extra={"creation_id": creation.id, "job_id": job.id, "queue_age_ms": round(queue_age_ms, 2)},
        )

        try:
            artifact = ModalGenerationClient().generate(creation.final_prompt)
            stored = AssetStore().store_bytes(
                creation.id,
                f"{job.id}.{artifact.file_extension}",
                artifact.data,
            )
            db.add(
                Asset(
                    creation_id=creation.id,
                    asset_type=AssetType.mesh.value,
                    storage_bucket=stored.bucket,
                    storage_key=stored.key,
                    mime_type=artifact.mime_type,
                    file_size=stored.size,
                )
            )
            job.provider_job_id = artifact.provider_job_id
            job.status = GenerationStatus.succeeded.value
            job.completed_at = datetime.now(timezone.utc)
            creation.status = CreationStatus.ready.value
            job.error_message = None
            duration_ms = (perf_counter() - started_at) * 1000
            db.commit()
            emit_metrics(
                [
                    MetricValue(name="GenerationCompletedCount", value=1),
                    MetricValue(name="GenerationDurationMs", value=duration_ms, unit="Milliseconds"),
                    MetricValue(name="AssetStoredBytes", value=stored.size, unit="Bytes"),
                ],
                dimensions={"Outcome": "succeeded"},
                properties={
                    "creation_id": creation.id,
                    "job_id": job.id,
                    "provider_job_id": artifact.provider_job_id,
                },
            )
            logger.info(
                "generation_succeeded",
                extra={
                    "creation_id": creation.id,
                    "job_id": job.id,
                    "provider_job_id": artifact.provider_job_id,
                    "duration_ms": round(duration_ms, 2),
                    "asset_size_bytes": stored.size,
                },
            )
            return True
        except Exception as exc:
            job.status = GenerationStatus.failed.value
            job.completed_at = datetime.now(timezone.utc)
            job.error_message = str(exc)
            creation.status = CreationStatus.failed.value
            duration_ms = (perf_counter() - started_at) * 1000
            emit_metrics(
                [
                    MetricValue(name="GenerationCompletedCount", value=1),
                    MetricValue(name="GenerationDurationMs", value=duration_ms, unit="Milliseconds"),
                ],
                dimensions={"Outcome": "failed"},
                properties={"creation_id": creation.id, "job_id": job.id},
            )
            logger.exception(
                "generation_failed",
                extra={"creation_id": creation.id, "job_id": job.id, "duration_ms": round(duration_ms, 2)},
            )
            db.commit()
            return True
        finally:
            clear_request_context()


def main() -> None:
    parser = argparse.ArgumentParser(description="Process GiftGen generation jobs")
    parser.add_argument("--watch", action="store_true", help="Poll continuously for queued jobs")
    parser.add_argument("--interval", type=int, default=5, help="Polling interval while watching")
    args = parser.parse_args()

    if not args.watch:
        process_next_job()
        return

    while True:
        worked = process_next_job()
        if not worked:
            time.sleep(args.interval)


if __name__ == "__main__":
    main()
