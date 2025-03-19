from __future__ import annotations

import argparse
import time
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.db.session import SessionLocal
from app.models import Asset, AssetType, CreationStatus, Creation, GenerationJob, GenerationStatus
from app.services.modal import ModalGenerationClient
from app.services.storage import AssetStore


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

        creation: Creation = job.creation
        job.status = GenerationStatus.running.value
        job.started_at = datetime.now(timezone.utc)
        creation.status = CreationStatus.running.value
        db.commit()

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
            job.status = GenerationStatus.succeeded.value
            job.completed_at = datetime.now(timezone.utc)
            creation.status = CreationStatus.ready.value
            job.error_message = None
        except Exception as exc:
            job.status = GenerationStatus.failed.value
            job.completed_at = datetime.now(timezone.utc)
            job.error_message = str(exc)
            creation.status = CreationStatus.failed.value

        db.commit()
        return True


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
