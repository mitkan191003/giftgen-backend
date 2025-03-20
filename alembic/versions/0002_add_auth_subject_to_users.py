"""add auth subject to users

Revision ID: 0002_add_auth_subject_to_users
Revises: 0001_initial_schema
Create Date: 2026-03-22
"""

from alembic import op
import sqlalchemy as sa


revision = "0002_add_auth_subject_to_users"
down_revision = "0001_initial_schema"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("users", sa.Column("auth_subject", sa.String(length=255), nullable=True))
    op.create_index(op.f("ix_users_auth_subject"), "users", ["auth_subject"], unique=True)


def downgrade() -> None:
    op.drop_index(op.f("ix_users_auth_subject"), table_name="users")
    op.drop_column("users", "auth_subject")
