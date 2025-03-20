from __future__ import annotations

import enum
import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, ForeignKey, JSON, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


def new_id() -> str:
    return str(uuid.uuid4())


class ConversationRole(str, enum.Enum):
    user = "user"
    assistant = "assistant"
    system = "system"


class CreationStatus(str, enum.Enum):
    draft = "draft"
    queued = "queued"
    running = "running"
    ready = "ready"
    failed = "failed"
    deleted = "deleted"


class Visibility(str, enum.Enum):
    private = "private"
    unlisted = "unlisted"
    public = "public"


class GenerationStatus(str, enum.Enum):
    draft = "draft"
    queued = "queued"
    running = "running"
    succeeded = "succeeded"
    failed = "failed"
    expired = "expired"
    deleted = "deleted"


class AssetType(str, enum.Enum):
    mesh = "mesh"
    preview = "preview"
    bundle = "bundle"
    metadata = "metadata"


class ShareType(str, enum.Enum):
    unlisted = "unlisted"
    public = "public"


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )


class User(TimestampMixin, Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    auth_subject: Mapped[str | None] = mapped_column(String(255), unique=True, nullable=True, index=True)
    display_name: Mapped[str | None] = mapped_column(String(120), nullable=True)
    auth_provider: Mapped[str] = mapped_column(String(50), default="development", nullable=False)

    threads: Mapped[list["ChatThread"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    creations: Mapped[list["Creation"]] = relationship(back_populates="user", cascade="all, delete-orphan")


class ChatThread(TimestampMixin, Base):
    __tablename__ = "chat_threads"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    title: Mapped[str | None] = mapped_column(String(200), nullable=True)

    user: Mapped["User"] = relationship(back_populates="threads")
    messages: Mapped[list["ChatMessage"]] = relationship(
        back_populates="thread", cascade="all, delete-orphan", order_by="ChatMessage.created_at"
    )
    creations: Mapped[list["Creation"]] = relationship(back_populates="source_thread")


class ChatMessage(Base):
    __tablename__ = "chat_messages"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    thread_id: Mapped[str] = mapped_column(
        ForeignKey("chat_threads.id", ondelete="CASCADE"), nullable=False, index=True
    )
    role: Mapped[str] = mapped_column(String(20), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    metadata_json: Mapped[dict[str, Any]] = mapped_column("metadata", JSON, default=dict, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    thread: Mapped["ChatThread"] = relationship(back_populates="messages")


class Creation(TimestampMixin, Base):
    __tablename__ = "creations"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    source_thread_id: Mapped[str | None] = mapped_column(
        ForeignKey("chat_threads.id", ondelete="SET NULL"), nullable=True, index=True
    )
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    final_prompt: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(20), default=CreationStatus.draft.value, nullable=False)
    visibility: Mapped[str] = mapped_column(String(20), default=Visibility.private.value, nullable=False)
    last_accessed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    user: Mapped["User"] = relationship(back_populates="creations")
    source_thread: Mapped["ChatThread | None"] = relationship(back_populates="creations")
    jobs: Mapped[list["GenerationJob"]] = relationship(
        back_populates="creation", cascade="all, delete-orphan", order_by="GenerationJob.created_at"
    )
    assets: Mapped[list["Asset"]] = relationship(
        back_populates="creation", cascade="all, delete-orphan", order_by="Asset.created_at"
    )
    shares: Mapped[list["Share"]] = relationship(
        back_populates="creation", cascade="all, delete-orphan", order_by="Share.created_at"
    )


class GenerationJob(Base):
    __tablename__ = "generation_jobs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    creation_id: Mapped[str] = mapped_column(
        ForeignKey("creations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    provider: Mapped[str] = mapped_column(String(40), default="modal", nullable=False)
    provider_job_id: Mapped[str | None] = mapped_column(String(200), nullable=True)
    model_name: Mapped[str] = mapped_column(String(120), default="trellis2", nullable=False)
    input_payload: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    status: Mapped[str] = mapped_column(String(20), default=GenerationStatus.draft.value, nullable=False)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    creation: Mapped["Creation"] = relationship(back_populates="jobs")


class Asset(Base):
    __tablename__ = "assets"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    creation_id: Mapped[str] = mapped_column(
        ForeignKey("creations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    asset_type: Mapped[str] = mapped_column(String(20), nullable=False)
    storage_bucket: Mapped[str] = mapped_column(String(255), nullable=False)
    storage_key: Mapped[str] = mapped_column(String(1024), nullable=False)
    mime_type: Mapped[str] = mapped_column(String(120), nullable=False)
    file_size: Mapped[int] = mapped_column(nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    creation: Mapped["Creation"] = relationship(back_populates="assets")


class Share(Base):
    __tablename__ = "shares"
    __table_args__ = (UniqueConstraint("share_slug", name="uq_shares_share_slug"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    creation_id: Mapped[str] = mapped_column(
        ForeignKey("creations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    share_type: Mapped[str] = mapped_column(String(20), nullable=False)
    share_slug: Mapped[str] = mapped_column(String(180), nullable=False, index=True)
    is_active: Mapped[bool] = mapped_column(default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    creation: Mapped["Creation"] = relationship(back_populates="shares")
