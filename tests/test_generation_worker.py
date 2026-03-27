from __future__ import annotations

from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

import app.workers.generation as generation_worker
from app.db.base import Base
from app.models import Asset, Creation, CreationStatus, GenerationJob, GenerationStatus, User, Visibility
from app.services.modal import GeneratedArtifact
from app.services.storage import StoredAsset


class FakeModalGenerationClient:
    def generate(self, prompt: str) -> GeneratedArtifact:
        assert prompt == "Make a tiny dragon"
        return GeneratedArtifact(
            data=b"glb-bytes",
            mime_type="model/gltf-binary",
            file_extension="glb",
            provider_job_id="modal-job-123",
        )


class FakeAssetStore:
    def store_bytes(self, creation_id: str, filename: str, data: bytes) -> StoredAsset:
        assert filename.endswith(".glb")
        assert data == b"glb-bytes"
        return StoredAsset(bucket="giftgen-dev-assets", key=f"creations/{creation_id}/{filename}", size=len(data))


def test_process_next_job_persists_success_state(monkeypatch, tmp_path) -> None:
    db_path = tmp_path / "giftgen-worker.db"
    engine = create_engine(
        f"sqlite+pysqlite:///{db_path}",
        future=True,
        connect_args={"check_same_thread": False},
    )
    test_session_local = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)
    Base.metadata.create_all(engine)

    monkeypatch.setattr(generation_worker, "SessionLocal", test_session_local)
    monkeypatch.setattr(generation_worker, "ModalGenerationClient", FakeModalGenerationClient)
    monkeypatch.setattr(generation_worker, "AssetStore", FakeAssetStore)

    with test_session_local() as db:
        user = User(email="dev@example.com", auth_provider="development")
        creation = Creation(
            user=user,
            title="Dragon gift",
            final_prompt="Make a tiny dragon",
            status=CreationStatus.queued.value,
            visibility=Visibility.private.value,
        )
        job = GenerationJob(
            creation=creation,
            status=GenerationStatus.queued.value,
            input_payload={"prompt": "Make a tiny dragon"},
        )
        db.add_all([user, creation, job])
        db.commit()
        creation_id = creation.id
        job_id = job.id

    assert generation_worker.process_next_job() is True

    with test_session_local() as db:
        job = db.scalar(select(GenerationJob).where(GenerationJob.id == job_id))
        creation = db.scalar(select(Creation).where(Creation.id == creation_id))
        assets = list(db.scalars(select(Asset).where(Asset.creation_id == creation_id)))

    assert job is not None
    assert creation is not None
    assert job.status == GenerationStatus.succeeded.value
    assert job.provider_job_id == "modal-job-123"
    assert job.completed_at is not None
    assert job.error_message is None
    assert creation.status == CreationStatus.ready.value
    assert len(assets) == 1
    assert assets[0].storage_bucket == "giftgen-dev-assets"
    assert assets[0].mime_type == "model/gltf-binary"
