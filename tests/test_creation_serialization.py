from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import create_engine, select
from sqlalchemy.orm import selectinload, sessionmaker

from app.api.routes.creations import _serialize_creation
from app.db.base import Base
from app.models import Asset, AssetType, Creation, CreationStatus, User, Visibility


def test_serialize_creation_after_commit_with_expired_state(tmp_path) -> None:
    db_path = tmp_path / "giftgen-creations.db"
    engine = create_engine(
        f"sqlite+pysqlite:///{db_path}",
        future=True,
        connect_args={"check_same_thread": False},
    )
    session_local = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)
    Base.metadata.create_all(engine)

    with session_local() as db:
        user = User(email="serialize@example.com", auth_provider="development")
        creation = Creation(
            user=user,
            title="A box",
            final_prompt="a box",
            status=CreationStatus.ready.value,
            visibility=Visibility.private.value,
        )
        asset = Asset(
            creation=creation,
            asset_type=AssetType.mesh.value,
            storage_bucket="giftgen-dev-assets",
            storage_key="creations/example/example.glb",
            mime_type="model/gltf-binary",
            file_size=1234,
        )
        db.add_all([user, creation, asset])
        db.commit()

    with session_local() as db:
        creation = db.scalar(
            select(Creation)
            .options(selectinload(Creation.assets))
            .where(Creation.title == "A box")
        )
        assert creation is not None
        creation.last_accessed_at = datetime.now(timezone.utc)
        db.commit()

        serialized = _serialize_creation(creation)

    assert serialized.id == creation.id
    assert serialized.status == CreationStatus.ready.value
    assert serialized.assets[0].download_url == f"/api/v1/assets/{serialized.assets[0].id}/content"
    assert serialized.assets[0].mime_type == "model/gltf-binary"
