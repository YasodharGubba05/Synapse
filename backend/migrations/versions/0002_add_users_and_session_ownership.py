"""Add authentication: users, auth_sessions, and meeting ownership.

`meeting_sessions.user_id` is nullable so meetings recorded before
authentication existed are kept intact. Those rows simply have no owner and
are therefore invisible to every account until they are claimed with
`python -m backend.cli claim-legacy-sessions --email <address>`.

Revision ID: 0002_auth
Revises: 0001_baseline
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0002_auth"
down_revision: Union[str, None] = "0001_baseline"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing_tables = set(inspector.get_table_names())

    if "users" not in existing_tables:
        op.create_table(
            "users",
            sa.Column("id", sa.String(), primary_key=True, nullable=False),
            sa.Column("email", sa.String(length=320), nullable=False),
            sa.Column("full_name", sa.String(length=120), nullable=True),
            sa.Column("password_hash", sa.String(length=512), nullable=False),
            sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("last_login_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("failed_login_count", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("locked_until", sa.DateTime(timezone=True), nullable=True),
        )
        op.create_index("ix_users_email", "users", ["email"], unique=True)

    if "auth_sessions" not in existing_tables:
        op.create_table(
            "auth_sessions",
            sa.Column("id", sa.String(), primary_key=True, nullable=False),
            sa.Column("user_id", sa.String(), nullable=False),
            sa.Column("refresh_token_hash", sa.String(length=128), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("last_used_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("user_agent", sa.String(length=400), nullable=True),
            sa.Column("ip_address", sa.String(length=64), nullable=True),
            sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        )
        op.create_index("ix_auth_sessions_user_id", "auth_sessions", ["user_id"])
        op.create_index(
            "ix_auth_sessions_refresh_token_hash", "auth_sessions", ["refresh_token_hash"]
        )

    meeting_columns = {col["name"] for col in inspector.get_columns("meeting_sessions")}
    if "user_id" not in meeting_columns:
        op.add_column("meeting_sessions", sa.Column("user_id", sa.String(), nullable=True))
        op.create_index("ix_meeting_sessions_user_id", "meeting_sessions", ["user_id"])
        if bind.dialect.name != "sqlite":
            # SQLite cannot add a foreign key to an existing table without
            # rebuilding it; ownership is enforced in the API layer regardless.
            op.create_foreign_key(
                "fk_meeting_sessions_user_id",
                "meeting_sessions",
                "users",
                ["user_id"],
                ["id"],
                ondelete="CASCADE",
            )


def downgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name != "sqlite":
        op.drop_constraint("fk_meeting_sessions_user_id", "meeting_sessions", type_="foreignkey")
    op.drop_index("ix_meeting_sessions_user_id", table_name="meeting_sessions")
    op.drop_column("meeting_sessions", "user_id")
    op.drop_index("ix_auth_sessions_refresh_token_hash", table_name="auth_sessions")
    op.drop_index("ix_auth_sessions_user_id", table_name="auth_sessions")
    op.drop_table("auth_sessions")
    op.drop_index("ix_users_email", table_name="users")
    op.drop_table("users")
