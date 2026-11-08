"""Operational CLI for Synapse.

Usage:
    python -m backend.cli migrate
    python -m backend.cli create-user --email you@example.com [--name "Your Name"]
    python -m backend.cli list-users
    python -m backend.cli claim-legacy-sessions --email you@example.com [--dry-run]
    python -m backend.cli purge-expired-sessions

`claim-legacy-sessions` assigns meetings that predate authentication (rows with
no owner) to an existing account, which is the safe migration path for data
recorded before this release.
"""
from __future__ import annotations

import argparse
import getpass
import sys
from pathlib import Path

if __package__ is None or __package__ == "":  # allow `python backend/cli.py`
    sys.path.append(str(Path(__file__).resolve().parent.parent))

from backend.config import settings
from backend.database import crud
from backend.database.connection import SessionLocal
from backend.database.models import MeetingSession
from backend.models.schemas import _validate_password_strength
from backend.security.passwords import hash_password


def cmd_migrate(_: argparse.Namespace) -> int:
    from backend.db_migrate import run_migrations

    run_migrations()
    print("Migrations applied (head).")
    return 0


def cmd_create_user(args: argparse.Namespace) -> int:
    db = SessionLocal()
    try:
        email = crud.normalize_email(args.email)
        if crud.get_user_by_email(db, email):
            print(f"An account already exists for {email}", file=sys.stderr)
            return 1
        password = args.password or getpass.getpass("Password: ")
        if not args.password:
            if password != getpass.getpass("Confirm password: "):
                print("Passwords do not match", file=sys.stderr)
                return 1
        try:
            _validate_password_strength(password)
        except ValueError as exc:
            print(f"Password rejected: {exc}", file=sys.stderr)
            return 1
        user = crud.create_user(db, email=email, password_hash=hash_password(password), full_name=args.name)
        print(f"Created user {user.email} (id={user.id})")
        return 0
    finally:
        db.close()


def cmd_list_users(_: argparse.Namespace) -> int:
    db = SessionLocal()
    try:
        from backend.database.models import User

        users = db.query(User).order_by(User.created_at).all()
        if not users:
            print("No users yet.")
            return 0
        for user in users:
            owned = db.query(MeetingSession).filter(MeetingSession.user_id == user.id).count()
            print(f"{user.id}  {user.email:40s} meetings={owned}  active={user.is_active}")
        return 0
    finally:
        db.close()


def cmd_claim_legacy_sessions(args: argparse.Namespace) -> int:
    db = SessionLocal()
    try:
        user = crud.get_user_by_email(db, args.email)
        if user is None:
            print(f"No account found for {args.email}. Create it first.", file=sys.stderr)
            return 1
        orphans = db.query(MeetingSession).filter(MeetingSession.user_id.is_(None)).all()
        if not orphans:
            print("No unowned meeting sessions found.")
            return 0
        print(f"Found {len(orphans)} unowned meeting session(s).")
        if args.dry_run:
            for meeting in orphans:
                print(f"  would assign {meeting.id}  {meeting.title!r}")
            print("Dry run - nothing changed.")
            return 0
        for meeting in orphans:
            meeting.user_id = user.id
        db.commit()
        print(f"Assigned {len(orphans)} meeting session(s) to {user.email}.")
        return 0
    finally:
        db.close()


def cmd_purge_expired_sessions(_: argparse.Namespace) -> int:
    db = SessionLocal()
    try:
        removed = crud.purge_expired_auth_sessions(db)
        print(f"Removed {removed} expired auth session row(s).")
        return 0
    finally:
        db.close()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m backend.cli", description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("migrate", help="Upgrade the database to the latest revision").set_defaults(
        func=cmd_migrate
    )

    create = sub.add_parser("create-user", help="Create an account from the command line")
    create.add_argument("--email", required=True)
    create.add_argument("--name", default=None)
    create.add_argument(
        "--password",
        default=None,
        help="Omit to be prompted (preferred - avoids the password in shell history)",
    )
    create.set_defaults(func=cmd_create_user)

    sub.add_parser("list-users", help="List accounts and their meeting counts").set_defaults(
        func=cmd_list_users
    )

    claim = sub.add_parser(
        "claim-legacy-sessions",
        help="Assign pre-authentication meetings to an existing account",
    )
    claim.add_argument("--email", required=True)
    claim.add_argument("--dry-run", action="store_true")
    claim.set_defaults(func=cmd_claim_legacy_sessions)

    sub.add_parser(
        "purge-expired-sessions", help="Delete expired auth_sessions rows"
    ).set_defaults(func=cmd_purge_expired_sessions)

    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
