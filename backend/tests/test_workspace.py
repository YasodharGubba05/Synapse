"""Meeting lifecycle, history hub, action items and legacy-data migration."""
from __future__ import annotations

from backend.database import crud
from backend.database.models import (
    ActionItem, ChatMessage, DecisionItem, MeetingSession, SuggestionItem, TranscriptEntry,
)
from tests.conftest import start_meeting


def test_meeting_start_returns_the_original_contract(alice):
    response = alice.post(
        "/api/meeting/start",
        json={"title": "Marketing Sync", "playbook": "sales", "meeting_memory": "Agenda: Q3"},
    )
    assert response.status_code == 200
    body = response.json()
    assert set(body) == {"session_id", "started_at", "status"}
    assert body["status"] == "active"
    assert body["session_id"]


def test_meeting_start_records_title_playbook_and_memory(alice):
    session_id = start_meeting(alice, title="Design Review", playbook="design")
    detail = alice.get(f"/api/history/{session_id}").json()
    assert detail["title"] == "Design Review"
    assert detail["playbook"] == "design"
    assert detail["meeting_memory"] == "notes"


def test_meeting_end_marks_the_session_ended(alice):
    session_id = start_meeting(alice)
    response = alice.post("/api/meeting/end", json={"session_id": session_id})
    assert response.status_code == 200
    body = response.json()
    assert set(body) == {"session_id", "ended_at", "status"}
    assert body["status"] == "ended"
    assert alice.get(f"/api/history/{session_id}").json()["status"] == "ended"


def test_history_summary_shape_is_unchanged(alice, db_session):
    session_id = start_meeting(alice, title="Standup")
    db_session.add(TranscriptEntry(session_id=session_id, text="hello", kind="speech"))
    db_session.add(ActionItem(session_id=session_id, task="Do the thing"))
    db_session.commit()

    rows = alice.get("/api/history").json()
    assert len(rows) == 1
    row = rows[0]
    assert set(row) == {
        "id", "title", "playbook", "started_at", "ended_at",
        "status", "transcript_count", "action_item_count",
    }
    assert row["transcript_count"] == 1
    assert row["action_item_count"] == 1


def test_history_detail_returns_every_collection(alice, db_session):
    session_id = start_meeting(alice)
    db_session.add_all(
        [
            TranscriptEntry(session_id=session_id, time_label="10:00:00", iso_time="iso", text="hi", kind="speech"),
            SuggestionItem(session_id=session_id, type="ANSWER", title="t", preview="p"),
            ChatMessage(session_id=session_id, role="user", content="question"),
            ActionItem(session_id=session_id, task="task", assignee="Alice", priority="high"),
            DecisionItem(session_id=session_id, content="decided"),
        ]
    )
    db_session.commit()

    detail = alice.get(f"/api/history/{session_id}").json()
    assert set(detail) == {
        "id", "title", "playbook", "started_at", "ended_at", "status", "meeting_memory",
        "transcript_entries", "suggestions", "chat_messages", "action_items", "decisions",
    }
    assert detail["transcript_entries"][0] == {
        "time": "10:00:00", "isoTime": "iso", "text": "hi", "kind": "speech"
    }
    assert detail["suggestions"][0] == {"type": "ANSWER", "title": "t", "preview": "p"}
    assert detail["chat_messages"][0] == {"role": "user", "content": "question"}
    assert detail["action_items"][0]["assignee"] == "Alice"
    assert detail["decisions"][0]["content"] == "decided"


def test_history_is_newest_first(alice):
    first = start_meeting(alice, title="First")
    second = start_meeting(alice, title="Second")
    ids = [row["id"] for row in alice.get("/api/history").json()]
    assert ids[0] == second and ids[1] == first


def test_rename_meeting(alice):
    session_id = start_meeting(alice, title="Old name")
    response = alice.put(f"/api/history/{session_id}/title", json={"title": "New name"})
    assert response.status_code == 200
    assert response.json() == {"id": session_id, "title": "New name"}
    assert alice.get(f"/api/history/{session_id}").json()["title"] == "New name"


def test_delete_meeting_cascades_to_its_children(alice, db_session):
    session_id = start_meeting(alice)
    db_session.add_all(
        [
            TranscriptEntry(session_id=session_id, text="x"),
            SuggestionItem(session_id=session_id, type="ANSWER", title="t", preview="p"),
            ChatMessage(session_id=session_id, role="user", content="c"),
            ActionItem(session_id=session_id, task="t"),
            DecisionItem(session_id=session_id, content="d"),
        ]
    )
    db_session.commit()

    assert alice.delete(f"/api/history/{session_id}").json() == {"deleted": True}
    db_session.expire_all()
    assert db_session.query(MeetingSession).filter(MeetingSession.id == session_id).first() is None
    for model in (TranscriptEntry, SuggestionItem, ChatMessage, ActionItem, DecisionItem):
        assert db_session.query(model).filter(model.session_id == session_id).count() == 0


def test_action_item_can_be_completed_and_reopened(alice, db_session):
    session_id = start_meeting(alice)
    item = ActionItem(session_id=session_id, task="Ship it")
    db_session.add(item)
    db_session.commit()

    done = alice.patch(f"/api/history/{session_id}/actions/{item.id}", json={"status": "completed"})
    assert done.json() == {"id": item.id, "status": "completed"}

    reopened = alice.patch(f"/api/history/{session_id}/actions/{item.id}", json={"status": "pending"})
    assert reopened.json()["status"] == "pending"


def test_action_item_status_is_validated(alice, db_session):
    session_id = start_meeting(alice)
    item = ActionItem(session_id=session_id, task="Ship it")
    db_session.add(item)
    db_session.commit()
    response = alice.patch(f"/api/history/{session_id}/actions/{item.id}", json={"status": "whatever"})
    assert response.status_code == 422


def test_action_item_can_be_deleted(alice, db_session):
    session_id = start_meeting(alice)
    item = ActionItem(session_id=session_id, task="Remove me")
    db_session.add(item)
    db_session.commit()
    item_id = item.id

    assert alice.delete(f"/api/history/{session_id}/actions/{item_id}").json() == {"deleted": True}
    db_session.expire_all()
    assert db_session.query(ActionItem).filter(ActionItem.id == item_id).first() is None


def test_missing_action_item_is_a_404(alice):
    session_id = start_meeting(alice)
    assert alice.delete(f"/api/history/{session_id}/actions/nope").status_code == 404


def test_deleting_a_user_removes_their_meetings_only(client, db_session):
    from tests.conftest import register

    first = register(client, "owner1@example.com")
    start_meeting(first)
    from fastapi.testclient import TestClient

    from backend.main import app

    with TestClient(app, base_url="http://testserver") as other:
        second = register(other, "owner2@example.com")
        kept = start_meeting(second)

    user = crud.get_user_by_id(db_session, first.user_id)
    db_session.delete(user)
    db_session.commit()

    remaining = {m.id for m in db_session.query(MeetingSession).all()}
    assert remaining == {kept}


# ── Legacy data migration path ────────────────────────────────────────────────

def test_claim_legacy_sessions_assigns_unowned_meetings(client, db_session):
    from backend.cli import main as cli_main
    from tests.conftest import register

    legacy = MeetingSession(title="Pre-auth meeting", playbook="general", user_id=None)
    db_session.add(legacy)
    db_session.commit()
    legacy_id = legacy.id

    user = register(client, "claimer@example.com")

    assert cli_main(["claim-legacy-sessions", "--email", "claimer@example.com", "--dry-run"]) == 0
    db_session.expire_all()
    assert db_session.query(MeetingSession).filter(MeetingSession.id == legacy_id).first().user_id is None

    assert cli_main(["claim-legacy-sessions", "--email", "claimer@example.com"]) == 0
    db_session.expire_all()
    claimed = db_session.query(MeetingSession).filter(MeetingSession.id == legacy_id).first()
    assert claimed.user_id == user.user_id

    # And it now shows up in that account's history.
    assert legacy_id in {row["id"] for row in user.get("/api/history").json()}


def test_claim_legacy_sessions_requires_an_existing_account():
    from backend.cli import main as cli_main

    assert cli_main(["claim-legacy-sessions", "--email", "nobody@example.com"]) == 1


# ── Transcript persistence ────────────────────────────────────────────────────

def test_transcript_entries_are_persisted_and_returned_by_history(alice, db_session):
    """The gap this closes: the live transcript used to exist only in browser
    memory, so every saved meeting came back from history with no transcript."""
    session_id = start_meeting(alice)

    first = alice.post(
        f"/api/history/{session_id}/transcript",
        json={"text": "Let us start the design review.", "time": "10:00:00",
              "isoTime": "2026-01-01T10:00:00Z", "kind": "speech"},
    )
    assert first.status_code == 201, first.text
    assert first.json()["id"]

    alice.post(
        f"/api/history/{session_id}/transcript",
        json={"text": "The login button is misaligned.", "time": "10:00:30",
              "isoTime": "2026-01-01T10:00:30Z", "kind": "speech"},
    )

    detail = alice.get(f"/api/history/{session_id}").json()
    assert [e["text"] for e in detail["transcript_entries"]] == [
        "Let us start the design review.",
        "The login button is misaligned.",
    ]
    assert detail["transcript_entries"][0] == {
        "time": "10:00:00",
        "isoTime": "2026-01-01T10:00:00Z",
        "text": "Let us start the design review.",
        "kind": "speech",
    }

    summary = next(r for r in alice.get("/api/history").json() if r["id"] == session_id)
    assert summary["transcript_count"] == 2

    assert db_session.query(TranscriptEntry).filter(
        TranscriptEntry.session_id == session_id
    ).count() == 2


def test_transcript_entry_requires_authentication(client):
    response = client.post("/api/history/some-id/transcript", json={"text": "hi"})
    assert response.status_code == 401


def test_cannot_write_a_transcript_into_someone_elses_meeting(alice, bob, db_session):
    session_id = start_meeting(alice)
    response = bob.post(
        f"/api/history/{session_id}/transcript", json={"text": "injected"}
    )
    assert response.status_code == 403
    assert db_session.query(TranscriptEntry).filter(
        TranscriptEntry.session_id == session_id
    ).count() == 0


def test_transcript_entry_rejects_empty_text(alice):
    session_id = start_meeting(alice)
    assert alice.post(f"/api/history/{session_id}/transcript", json={"text": ""}).status_code == 422


def test_transcript_entry_rejects_an_unknown_kind(alice):
    session_id = start_meeting(alice)
    response = alice.post(
        f"/api/history/{session_id}/transcript", json={"text": "hi", "kind": "shouting"}
    )
    assert response.status_code == 422


def test_deleting_a_meeting_removes_its_transcript(alice, db_session):
    session_id = start_meeting(alice)
    alice.post(f"/api/history/{session_id}/transcript", json={"text": "to be deleted"})
    alice.delete(f"/api/history/{session_id}")
    db_session.expire_all()
    assert db_session.query(TranscriptEntry).filter(
        TranscriptEntry.session_id == session_id
    ).count() == 0
