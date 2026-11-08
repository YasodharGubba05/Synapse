"""Baseline: the original six meeting tables.

Written defensively so that `alembic upgrade head` works both on a brand new
database (fresh Render/PostgreSQL deployment) and on an existing SQLite file
created by the pre-Alembic `Base.metadata.create_all()` path: any table that
is already present is left exactly as it is, so existing meeting data is
preserved rather than recreated.

Revision ID: 0001_baseline
Revises:
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0001_baseline"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _existing_tables() -> set[str]:
    return set(sa.inspect(op.get_bind()).get_table_names())


def upgrade() -> None:
    existing = _existing_tables()

    if "meeting_sessions" not in existing:
        op.create_table(
            "meeting_sessions",
            sa.Column("id", sa.String(), primary_key=True, nullable=False),
            sa.Column("title", sa.String(), nullable=False),
            sa.Column("playbook", sa.String(), nullable=False),
            sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("ended_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("meeting_memory", sa.Text(), nullable=True),
            sa.Column("status", sa.String(), nullable=True),
        )

    child_tables = {
        "transcript_entries": [
            sa.Column("time_label", sa.String(), nullable=True),
            sa.Column("iso_time", sa.String(), nullable=True),
            sa.Column("text", sa.Text(), nullable=True),
            sa.Column("kind", sa.String(), nullable=True),
        ],
        "suggestion_items": [
            sa.Column("type", sa.String(), nullable=True),
            sa.Column("title", sa.String(), nullable=True),
            sa.Column("preview", sa.Text(), nullable=True),
        ],
        "chat_messages": [
            sa.Column("role", sa.String(), nullable=True),
            sa.Column("content", sa.Text(), nullable=True),
        ],
        "action_items": [
            sa.Column("task", sa.Text(), nullable=True),
            sa.Column("assignee", sa.String(), nullable=True),
            sa.Column("priority", sa.String(), nullable=True),
            sa.Column("status", sa.String(), nullable=True),
        ],
        "decision_items": [
            sa.Column("content", sa.Text(), nullable=True),
        ],
    }

    for table_name, payload_columns in child_tables.items():
        if table_name in existing:
            continue
        op.create_table(
            table_name,
            sa.Column("id", sa.String(), primary_key=True, nullable=False),
            sa.Column("session_id", sa.String(), nullable=False),
            *payload_columns,
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
            sa.ForeignKeyConstraint(["session_id"], ["meeting_sessions.id"]),
        )


def downgrade() -> None:
    for table_name in (
        "decision_items",
        "action_items",
        "chat_messages",
        "suggestion_items",
        "transcript_entries",
        "meeting_sessions",
    ):
        op.drop_table(table_name)
