"""Endpoint protection, user-level data isolation and IDOR prevention."""
from __future__ import annotations

import pytest

from backend.database.models import ActionItem
from tests.conftest import start_meeting

GROQ_HEADER = {"X-Groq-API-Key": "gsk_test_key"}

# (method, path, needs a json body)
PROTECTED_ENDPOINTS = [
    ("get", "/api/history", None),
    ("get", "/api/history/some-id", None),
    ("put", "/api/history/some-id/title", {"title": "x"}),
    ("delete", "/api/history/some-id", None),
    ("patch", "/api/history/some-id/actions/item-id", {"status": "completed"}),
    ("delete", "/api/history/some-id/actions/item-id", None),
    ("post", "/api/meeting/start", {"title": "x", "playbook": "general"}),
    ("post", "/api/meeting/end", {"session_id": "some-id"}),
    ("post", "/api/suggestions", {"transcript_slice": "hello"}),
    ("post", "/api/intelligence", {"transcript_slice": "hello"}),
    ("post", "/api/chat", {"message": "hi", "full_transcript": "hello"}),
]

PUBLIC_ENDPOINTS = [
    ("get", "/"),
    ("get", "/api/health"),
    ("get", "/healthz"),
]


@pytest.mark.parametrize("method,path,body", PROTECTED_ENDPOINTS)
def test_protected_endpoints_reject_anonymous_callers(client, method, path, body):
    kwargs = {"headers": GROQ_HEADER}
    if body is not None:
        kwargs["json"] = body
    response = getattr(client, method)(path, **kwargs)
    assert response.status_code == 401, f"{method.upper()} {path} -> {response.status_code}"


def test_transcribe_rejects_anonymous_callers(client):
    response = client.post(
        "/api/transcribe",
        headers=GROQ_HEADER,
        files={"audio_file": ("a.webm", b"x" * 2000, "audio/webm")},
    )
    assert response.status_code == 401


@pytest.mark.parametrize("method,path", PUBLIC_ENDPOINTS)
def test_health_endpoints_stay_public(client, method, path):
    assert getattr(client, method)(path).status_code == 200


def test_unprefixed_paths_are_protected_too(client):
    """Routers are mounted at both /api/... and /...; both need auth."""
    assert client.get("/history").status_code == 401
    assert client.post("/meeting/start", headers=GROQ_HEADER, json={"title": "x"}).status_code == 401


# ── Ownership ─────────────────────────────────────────────────────────────────

def test_history_only_lists_your_own_meetings(alice, bob):
    alice_session = start_meeting(alice, title="Alice standup")
    bob_session = start_meeting(bob, title="Bob sales call")

    alice_ids = {row["id"] for row in alice.get("/api/history").json()}
    bob_ids = {row["id"] for row in bob.get("/api/history").json()}

    assert alice_ids == {alice_session}
    assert bob_ids == {bob_session}


def test_reading_another_users_meeting_is_forbidden(alice, bob):
    alice_session = start_meeting(alice)
    response = bob.get(f"/api/history/{alice_session}")
    assert response.status_code == 403
    assert "do not have access" in response.json()["detail"]


def test_missing_meeting_is_a_404_not_a_403(alice):
    assert alice.get("/api/history/does-not-exist").status_code == 404


def test_renaming_another_users_meeting_is_forbidden(alice, bob):
    alice_session = start_meeting(alice, title="Private")
    assert bob.put(f"/api/history/{alice_session}/title", json={"title": "Hijacked"}).status_code == 403
    # The title is untouched.
    assert alice.get(f"/api/history/{alice_session}").json()["title"] == "Private"


def test_deleting_another_users_meeting_is_forbidden(alice, bob):
    alice_session = start_meeting(alice)
    assert bob.delete(f"/api/history/{alice_session}").status_code == 403
    assert alice.get(f"/api/history/{alice_session}").status_code == 200


def test_ending_another_users_meeting_is_forbidden(alice, bob):
    alice_session = start_meeting(alice)
    response = bob.post("/api/meeting/end", json={"session_id": alice_session})
    assert response.status_code == 403
    assert alice.get(f"/api/history/{alice_session}").json()["status"] == "active"


@pytest.mark.parametrize(
    "path,payload_key",
    [
        ("/api/suggestions", "transcript_slice"),
        ("/api/intelligence", "transcript_slice"),
    ],
)
def test_ai_endpoints_reject_another_users_session_id(alice, bob, path, payload_key):
    """session_id in the request *body* is checked, not just path parameters."""
    alice_session = start_meeting(alice)
    response = bob.post(path, json={payload_key: "some transcript text", "session_id": alice_session})
    assert response.status_code == 403


def test_chat_rejects_another_users_session_id(alice, bob):
    alice_session = start_meeting(alice)
    response = bob.post(
        "/api/chat",
        json={"message": "hi", "full_transcript": "text", "session_id": alice_session},
    )
    assert response.status_code == 403


def test_action_items_cannot_be_touched_across_users(alice, bob, db_session):
    alice_session = start_meeting(alice)
    item = ActionItem(session_id=alice_session, task="Ship the release", priority="high")
    db_session.add(item)
    db_session.commit()
    item_id = item.id

    assert bob.patch(
        f"/api/history/{alice_session}/actions/{item_id}", json={"status": "completed"}
    ).status_code == 403
    assert bob.delete(f"/api/history/{alice_session}/actions/{item_id}").status_code == 403

    db_session.expire_all()
    assert db_session.query(ActionItem).filter(ActionItem.id == item_id).first().status == "pending"


def test_action_item_from_another_session_is_not_reachable(alice, db_session):
    """Pairing your own session_id with someone else's item id must not work."""
    session_a = start_meeting(alice, title="A")
    session_b = start_meeting(alice, title="B")
    item = ActionItem(session_id=session_b, task="Belongs to B")
    db_session.add(item)
    db_session.commit()

    response = alice.patch(
        f"/api/history/{session_a}/actions/{item.id}", json={"status": "completed"}
    )
    assert response.status_code == 404


def test_meeting_is_recorded_against_its_creator(alice, db_session):
    from backend.database.models import MeetingSession

    session_id = start_meeting(alice)
    meeting = db_session.query(MeetingSession).filter(MeetingSession.id == session_id).first()
    assert meeting.user_id == alice.user_id


def test_legacy_unowned_meetings_are_invisible(alice, db_session):
    """Meetings that predate authentication stay in the database but are not
    served to any account until they are explicitly claimed."""
    from backend.database.models import MeetingSession

    legacy = MeetingSession(title="Pre-auth meeting", playbook="general", user_id=None)
    db_session.add(legacy)
    db_session.commit()

    assert legacy.id not in {row["id"] for row in alice.get("/api/history").json()}
    assert alice.get(f"/api/history/{legacy.id}").status_code == 403
    # Still present on disk - nothing was deleted.
    db_session.expire_all()
    assert db_session.query(MeetingSession).filter(MeetingSession.id == legacy.id).first() is not None
