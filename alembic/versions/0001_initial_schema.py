"""initial schema

Revision ID: 0001_initial_schema
Revises:
Create Date: 2026-03-20
"""

from alembic import op
import sqlalchemy as sa


revision = "0001_initial_schema"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("display_name", sa.String(length=120), nullable=True),
        sa.Column("auth_provider", sa.String(length=50), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_users")),
        sa.UniqueConstraint("email", name=op.f("uq_users_email")),
    )
    op.create_index(op.f("ix_users_email"), "users", ["email"], unique=False)

    op.create_table(
        "chat_threads",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("title", sa.String(length=200), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], name=op.f("fk_chat_threads_user_id_users"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_chat_threads")),
    )
    op.create_index(op.f("ix_chat_threads_user_id"), "chat_threads", ["user_id"], unique=False)

    op.create_table(
        "chat_messages",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("thread_id", sa.String(length=36), nullable=False),
        sa.Column("role", sa.String(length=20), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("metadata", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["thread_id"], ["chat_threads.id"], name=op.f("fk_chat_messages_thread_id_chat_threads"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_chat_messages")),
    )
    op.create_index(op.f("ix_chat_messages_thread_id"), "chat_messages", ["thread_id"], unique=False)

    op.create_table(
        "creations",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("source_thread_id", sa.String(length=36), nullable=True),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("final_prompt", sa.Text(), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("visibility", sa.String(length=20), nullable=False),
        sa.Column("last_accessed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["source_thread_id"], ["chat_threads.id"], name=op.f("fk_creations_source_thread_id_chat_threads"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], name=op.f("fk_creations_user_id_users"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_creations")),
    )
    op.create_index(op.f("ix_creations_source_thread_id"), "creations", ["source_thread_id"], unique=False)
    op.create_index(op.f("ix_creations_user_id"), "creations", ["user_id"], unique=False)

    op.create_table(
        "generation_jobs",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("creation_id", sa.String(length=36), nullable=False),
        sa.Column("provider", sa.String(length=40), nullable=False),
        sa.Column("provider_job_id", sa.String(length=200), nullable=True),
        sa.Column("model_name", sa.String(length=120), nullable=False),
        sa.Column("input_payload", sa.JSON(), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["creation_id"], ["creations.id"], name=op.f("fk_generation_jobs_creation_id_creations"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_generation_jobs")),
    )
    op.create_index(op.f("ix_generation_jobs_creation_id"), "generation_jobs", ["creation_id"], unique=False)

    op.create_table(
        "assets",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("creation_id", sa.String(length=36), nullable=False),
        sa.Column("asset_type", sa.String(length=20), nullable=False),
        sa.Column("storage_bucket", sa.String(length=255), nullable=False),
        sa.Column("storage_key", sa.String(length=1024), nullable=False),
        sa.Column("mime_type", sa.String(length=120), nullable=False),
        sa.Column("file_size", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["creation_id"], ["creations.id"], name=op.f("fk_assets_creation_id_creations"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_assets")),
    )
    op.create_index(op.f("ix_assets_creation_id"), "assets", ["creation_id"], unique=False)

    op.create_table(
        "shares",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("creation_id", sa.String(length=36), nullable=False),
        sa.Column("share_type", sa.String(length=20), nullable=False),
        sa.Column("share_slug", sa.String(length=180), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["creation_id"], ["creations.id"], name=op.f("fk_shares_creation_id_creations"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_shares")),
        sa.UniqueConstraint("share_slug", name=op.f("uq_shares_share_slug")),
    )
    op.create_index(op.f("ix_shares_creation_id"), "shares", ["creation_id"], unique=False)
    op.create_index(op.f("ix_shares_share_slug"), "shares", ["share_slug"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_shares_share_slug"), table_name="shares")
    op.drop_index(op.f("ix_shares_creation_id"), table_name="shares")
    op.drop_table("shares")

    op.drop_index(op.f("ix_assets_creation_id"), table_name="assets")
    op.drop_table("assets")

    op.drop_index(op.f("ix_generation_jobs_creation_id"), table_name="generation_jobs")
    op.drop_table("generation_jobs")

    op.drop_index(op.f("ix_creations_user_id"), table_name="creations")
    op.drop_index(op.f("ix_creations_source_thread_id"), table_name="creations")
    op.drop_table("creations")

    op.drop_index(op.f("ix_chat_messages_thread_id"), table_name="chat_messages")
    op.drop_table("chat_messages")

    op.drop_index(op.f("ix_chat_threads_user_id"), table_name="chat_threads")
    op.drop_table("chat_threads")

    op.drop_index(op.f("ix_users_email"), table_name="users")
    op.drop_table("users")
