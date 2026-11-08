"""Regression cover for the pre-existing AI/audio behaviour.

Groq is stubbed at the client boundary so the extraction pipeline, retries,
fallbacks, playbooks, streaming and persistence are all exercised without
network access or a real API key.
"""
from __future__ import annotations

import json

import pytest
from fastapi import HTTPException

from backend.database.models import ActionItem, ChatMessage, DecisionItem, SuggestionItem
from backend.prompts.defaults import PLAYBOOK_PROMPTS
from tests.conftest import start_meeting


def _completion(content: str) -> dict:
    return {"choices": [{"message": {"content": content}}]}


def _three_suggestions() -> str:
    return json.dumps(
        {
            "suggestions": [
                {"type": "QUESTION_TO_ASK", "title": "Scope", "preview": "Ask about scope."},
                {"type": "TALKING_POINT", "title": "Timeline", "preview": "Mention the timeline."},
                {"type": "ANSWER", "title": "Budget", "preview": "The budget is approved."},
            ]
        }
    )


# ── Transcription ─────────────────────────────────────────────────────────────

def test_transcription_returns_text_and_forwards_the_callers_key(alice, monkeypatch):
    seen = {}

    async def fake_multipart(api_key, files, data):
        seen["api_key"] = api_key
        seen["model"] = data["model"]
        seen["content_type"] = files["file"][2]
        return {"text": "Hello team, let's start the design review."}

    monkeypatch.setattr("backend.routers.transcribe.groq_post_multipart", fake_multipart)

    response = alice.post(
        "/api/transcribe",
        files={"audio_file": ("meeting-audio.webm", b"\x1a\x45\xdf\xa3" + b"0" * 4000, "audio/webm")},
    )
    assert response.status_code == 200
    assert response.json()["text"] == "Hello team, let's start the design review."
    assert seen["api_key"] == "gsk_test_key_never_persisted"
    assert seen["model"] == "whisper-large-v3"
    assert seen["content_type"] == "audio/webm"


def test_tiny_audio_chunk_is_skipped_silently(alice, monkeypatch):
    async def should_not_run(*_a, **_kw):  # pragma: no cover
        raise AssertionError("Groq must not be called for a tiny blob")

    monkeypatch.setattr("backend.routers.transcribe.groq_post_multipart", should_not_run)
    response = alice.post("/api/transcribe", files={"audio_file": ("a.webm", b"tiny", "audio/webm")})
    assert response.status_code == 200
    assert response.json() == {"text": ""}


def test_transcription_failure_degrades_to_empty_text(alice, monkeypatch):
    async def boom(*_a, **_kw):
        raise HTTPException(status_code=400, detail="could not process file")

    monkeypatch.setattr("backend.routers.transcribe.groq_post_multipart", boom)
    response = alice.post(
        "/api/transcribe", files={"audio_file": ("a.webm", b"x" * 4000, "audio/webm")}
    )
    assert response.status_code == 200
    body = response.json()
    assert body["text"] == ""
    assert "could not process file" in body["error"]


def test_transcription_error_never_echoes_the_groq_key(alice, monkeypatch):
    key = "gsk_test_key_never_persisted"

    async def leaky(api_key, files, data):
        raise HTTPException(status_code=401, detail=f"Invalid API key: {api_key}")

    monkeypatch.setattr("backend.routers.transcribe.groq_post_multipart", leaky)
    response = alice.post(
        "/api/transcribe", files={"audio_file": ("a.webm", b"x" * 4000, "audio/webm")}
    )
    assert key not in response.text


# ── Suggestions: three per cycle, playbooks, retries, failure ─────────────────

def test_suggestions_returns_exactly_three_and_persists_them(alice, db_session, monkeypatch):
    session_id = start_meeting(alice)

    async def fake_post(endpoint, api_key, payload):
        return _completion(_three_suggestions())

    monkeypatch.setattr("backend.routers.suggestions.groq_post", fake_post)

    response = alice.post(
        "/api/suggestions",
        json={"transcript_slice": "we discussed the launch", "session_id": session_id, "playbook": "sales"},
    )
    assert response.status_code == 200
    suggestions = response.json()["suggestions"]
    assert len(suggestions) == 3
    assert {s["type"] for s in suggestions} == {"QUESTION_TO_ASK", "TALKING_POINT", "ANSWER"}

    stored = db_session.query(SuggestionItem).filter(SuggestionItem.session_id == session_id).all()
    assert len(stored) == 3


@pytest.mark.parametrize("playbook", ["general", "standup", "design", "sales"])
def test_all_four_playbooks_select_their_own_prompt(alice, monkeypatch, playbook):
    captured = {}

    async def fake_post(endpoint, api_key, payload):
        captured["system"] = payload["messages"][0]["content"]
        return _completion(_three_suggestions())

    monkeypatch.setattr("backend.routers.suggestions.groq_post", fake_post)

    response = alice.post(
        "/api/suggestions", json={"transcript_slice": "text", "playbook": playbook}
    )
    assert response.status_code == 200
    assert captured["system"] == PLAYBOOK_PROMPTS[playbook]


def test_suggestions_retry_recovers_from_a_malformed_first_answer(alice, monkeypatch):
    calls = {"n": 0}

    async def flaky(endpoint, api_key, payload):
        calls["n"] += 1
        if calls["n"] == 1:
            return _completion("not json at all")
        if calls["n"] == 2:
            return _completion(json.dumps({"suggestions": [{"type": "ANSWER", "title": "x", "preview": "y"}]}))
        return _completion(_three_suggestions())

    monkeypatch.setattr("backend.routers.suggestions.groq_post", flaky)

    response = alice.post("/api/suggestions", json={"transcript_slice": "text"})
    assert response.status_code == 200
    assert calls["n"] == 3  # three-attempt ladder, succeeding on the last
    assert len(response.json()["suggestions"]) == 3


def test_suggestions_gives_up_after_three_attempts(alice, monkeypatch):
    calls = {"n": 0}

    async def always_bad(endpoint, api_key, payload):
        calls["n"] += 1
        return _completion("{}")

    monkeypatch.setattr("backend.routers.suggestions.groq_post", always_bad)
    response = alice.post("/api/suggestions", json={"transcript_slice": "text"})
    assert response.status_code == 500
    assert calls["n"] == 3


def test_suggestions_custom_prompt_overrides_the_playbook(alice, monkeypatch):
    captured = {}

    async def fake_post(endpoint, api_key, payload):
        captured["system"] = payload["messages"][0]["content"]
        return _completion(_three_suggestions())

    monkeypatch.setattr("backend.routers.suggestions.groq_post", fake_post)
    alice.post(
        "/api/suggestions",
        json={"transcript_slice": "text", "suggestions_prompt": "MY CUSTOM PROMPT", "playbook": "design"},
    )
    assert captured["system"] == "MY CUSTOM PROMPT"


def test_suggestions_trims_the_transcript_to_the_context_window(alice, monkeypatch):
    captured = {}

    async def fake_post(endpoint, api_key, payload):
        captured["user"] = payload["messages"][1]["content"]
        return _completion(_three_suggestions())

    monkeypatch.setattr("backend.routers.suggestions.groq_post", fake_post)
    words = " ".join(f"w{i}" for i in range(500))
    alice.post("/api/suggestions", json={"transcript_slice": words, "context_window": 10})
    transcript_block = captured["user"].split("<transcript>")[1].split("</transcript>")[0].strip()
    assert transcript_block.split() == [f"w{i}" for i in range(490, 500)]


# ── Intelligence: structured extraction, validation, fallback ─────────────────

def test_intelligence_extracts_and_persists_actions_and_decisions(alice, db_session, monkeypatch):
    session_id = start_meeting(alice)

    async def fake_post(endpoint, api_key, payload):
        return _completion(
            json.dumps(
                {
                    "sentiment": "constructive",
                    "action_items": [
                        {"task": "Send the recap", "assignee": "Alice", "priority": "high"},
                        {"task": "Review the mock", "assignee": None, "priority": "low"},
                    ],
                    "decisions": ["Ship on Friday"],
                    "keywords": ["launch", "recap"],
                }
            )
        )

    monkeypatch.setattr("backend.routers.intelligence.groq_post", fake_post)

    response = alice.post(
        "/api/intelligence", json={"transcript_slice": "a long transcript", "session_id": session_id}
    )
    assert response.status_code == 200
    body = response.json()
    assert body["sentiment"] == "constructive"
    assert len(body["action_items"]) == 2
    assert body["action_items"][0]["priority"] == "high"
    assert body["decisions"] == ["Ship on Friday"]
    assert body["keywords"] == ["launch", "recap"]

    assert db_session.query(ActionItem).filter(ActionItem.session_id == session_id).count() == 2
    assert db_session.query(DecisionItem).filter(DecisionItem.session_id == session_id).count() == 1


def test_intelligence_falls_back_to_an_empty_schema_on_bad_json(alice, monkeypatch):
    async def fake_post(endpoint, api_key, payload):
        return _completion("this is not json")

    monkeypatch.setattr("backend.routers.intelligence.groq_post", fake_post)
    response = alice.post("/api/intelligence", json={"transcript_slice": "text"})
    assert response.status_code == 200
    assert response.json() == {
        "sentiment": "neutral",
        "action_items": [],
        "decisions": [],
        "keywords": [],
    }


def test_intelligence_propagates_a_groq_error_status(alice, monkeypatch):
    async def fake_post(endpoint, api_key, payload):
        raise HTTPException(status_code=429, detail="rate limited upstream")

    monkeypatch.setattr("backend.routers.intelligence.groq_post", fake_post)
    response = alice.post("/api/intelligence", json={"transcript_slice": "text"})
    assert response.status_code == 429


def test_intelligence_uses_the_requested_model(alice, monkeypatch):
    captured = {}

    async def fake_post(endpoint, api_key, payload):
        captured["model"] = payload["model"]
        return _completion('{"sentiment":"neutral","action_items":[],"decisions":[],"keywords":[]}')

    monkeypatch.setattr("backend.routers.intelligence.groq_post", fake_post)
    alice.post(
        "/api/intelligence",
        json={"transcript_slice": "text", "model": "openai/gpt-oss-120b"},
    )
    assert captured["model"] == "openai/gpt-oss-120b"


# ── Streaming copilot ─────────────────────────────────────────────────────────

def _sse_chunks(tokens: list[str]):
    async def generator(api_key, payload):
        for token in tokens:
            yield "data: " + json.dumps({"choices": [{"delta": {"content": token}}]}) + "\n\n"
        yield "data: [DONE]\n\n"

    return generator


def test_chat_streams_server_sent_events_and_saves_both_messages(alice, db_session, monkeypatch):
    session_id = start_meeting(alice)
    monkeypatch.setattr(
        "backend.routers.chat.iter_groq_chat_stream",
        _sse_chunks(["The ", "login ", "button."]),
    )

    with alice.raw.stream(
        "POST",
        "/api/chat",
        headers={"X-Groq-API-Key": "gsk_test_key_never_persisted", "X-CSRF-Token": alice.csrf},
        json={"message": "What was discussed?", "full_transcript": "login button styling", "session_id": session_id},
    ) as response:
        assert response.status_code == 200
        assert response.headers["content-type"].startswith("text/event-stream")
        body = "".join(response.iter_text())

    assert body.count("data: ") == 4
    assert "[DONE]" in body

    messages = (
        db_session.query(ChatMessage)
        .filter(ChatMessage.session_id == session_id)
        .order_by(ChatMessage.created_at)
        .all()
    )
    roles = [m.role for m in messages]
    assert "user" in roles and "assistant" in roles
    assistant = next(m for m in messages if m.role == "assistant")
    assert assistant.content == "The login button."


def test_chat_suggestion_mode_uses_the_detail_prompt(alice, monkeypatch):
    captured = {}

    def capturing(api_key, payload):
        captured["system"] = payload["messages"][0]["content"]
        return _sse_chunks(["ok"])(api_key, payload)

    monkeypatch.setattr("backend.routers.chat.iter_groq_chat_stream", capturing)
    response = alice.post(
        "/api/chat",
        json={
            "message": "expand",
            "full_transcript": "transcript text",
            "mode": "suggestion",
            "detail_prompt": "DETAIL PROMPT {{FULL_TRANSCRIPT}}",
        },
    )
    assert response.status_code == 200
    assert captured["system"] == "DETAIL PROMPT transcript text"


def test_chat_appends_meeting_memory_to_the_system_prompt(alice, monkeypatch):
    captured = {}

    def capturing(api_key, payload):
        captured["system"] = payload["messages"][0]["content"]
        return _sse_chunks(["ok"])(api_key, payload)

    monkeypatch.setattr("backend.routers.chat.iter_groq_chat_stream", capturing)
    alice.post(
        "/api/chat",
        json={"message": "hi", "full_transcript": "t", "meeting_memory": "Agenda: pricing"},
    )
    assert "<meeting_memory>" in captured["system"]
    assert "Agenda: pricing" in captured["system"]


def test_chat_forwards_prior_history(alice, monkeypatch):
    captured = {}

    def capturing(api_key, payload):
        captured["messages"] = payload["messages"]
        return _sse_chunks(["ok"])(api_key, payload)

    monkeypatch.setattr("backend.routers.chat.iter_groq_chat_stream", capturing)
    alice.post(
        "/api/chat",
        json={
            "message": "and then?",
            "full_transcript": "t",
            "history": [
                {"role": "user", "content": "first"},
                {"role": "assistant", "content": "second"},
            ],
        },
    )
    roles = [m["role"] for m in captured["messages"]]
    assert roles == ["system", "user", "assistant", "user"]
    assert captured["messages"][-1]["content"] == "and then?"


def test_chat_stream_reports_an_upstream_failure_instead_of_dying(alice, monkeypatch):
    """A Groq rejection arrives after the 200 headers are already sent, so it
    must come back as an SSE error frame rather than a dropped connection."""
    async def failing_stream(api_key, payload):
        raise HTTPException(status_code=401, detail=f"Invalid API Key: {api_key}")
        yield  # pragma: no cover - makes this an async generator

    monkeypatch.setattr("backend.routers.chat.iter_groq_chat_stream", failing_stream)

    with alice.raw.stream(
        "POST",
        "/api/chat",
        headers={"X-Groq-API-Key": "gsk_test_key_never_persisted", "X-CSRF-Token": alice.csrf},
        json={"message": "hi", "full_transcript": "text"},
    ) as response:
        assert response.status_code == 200
        body = "".join(response.iter_text())

    assert '"error"' in body
    assert '"status": 401' in body
    assert body.rstrip().endswith("[DONE]")
    # The key must not be echoed back to the browser.
    assert "gsk_test_key_never_persisted" not in body
    assert "[redacted]" in body


# ── Action item id round-trip ────────────────────────────────────────────────

def _intelligence_with_two_actions(monkeypatch):
    async def fake_post(endpoint, api_key, payload):
        return _completion(
            json.dumps(
                {
                    "sentiment": "neutral",
                    "action_items": [
                        {"task": "Send the recap", "assignee": "Alice", "priority": "high"},
                        {"task": "Book the room", "assignee": None, "priority": "low"},
                    ],
                    "decisions": [],
                    "keywords": [],
                }
            )
        )

    monkeypatch.setattr("backend.routers.intelligence.groq_post", fake_post)


def test_intelligence_returns_the_database_id_of_each_saved_action_item(alice, db_session, monkeypatch):
    """The gap this closes: without an id the client invented a local one, so
    completing an action item during a live meeting was never saved."""
    session_id = start_meeting(alice)
    _intelligence_with_two_actions(monkeypatch)

    response = alice.post(
        "/api/intelligence", json={"transcript_slice": "text", "session_id": session_id}
    )
    assert response.status_code == 200
    returned_ids = [item["id"] for item in response.json()["action_items"]]
    assert all(returned_ids), "every persisted action item must carry its id"

    stored_ids = {
        row.id for row in db_session.query(ActionItem).filter(ActionItem.session_id == session_id)
    }
    assert set(returned_ids) == stored_ids


def test_returned_action_item_id_can_immediately_be_completed(alice, db_session, monkeypatch):
    """End-to-end of the fix: take the id straight from /intelligence and use
    it on the history endpoint, exactly as the workspace does."""
    session_id = start_meeting(alice)
    _intelligence_with_two_actions(monkeypatch)

    item_id = alice.post(
        "/api/intelligence", json={"transcript_slice": "text", "session_id": session_id}
    ).json()["action_items"][0]["id"]

    patched = alice.patch(
        f"/api/history/{session_id}/actions/{item_id}", json={"status": "completed"}
    )
    assert patched.status_code == 200
    assert patched.json() == {"id": item_id, "status": "completed"}

    db_session.expire_all()
    assert db_session.query(ActionItem).filter(ActionItem.id == item_id).first().status == "completed"


def test_action_items_have_no_id_when_the_meeting_is_not_persisted(alice, monkeypatch):
    """No session_id means nothing was saved, so there is no id to hand back
    and the client is right to use a local one."""
    _intelligence_with_two_actions(monkeypatch)
    response = alice.post("/api/intelligence", json={"transcript_slice": "text"})
    assert response.status_code == 200
    assert all(item["id"] is None for item in response.json()["action_items"])


def test_model_supplied_ids_are_never_trusted(alice, db_session, monkeypatch):
    """If the LLM hallucinates an id field it must be overwritten by the real
    database id, never used to address someone else's row."""
    session_id = start_meeting(alice)

    async def fake_post(endpoint, api_key, payload):
        return _completion(
            json.dumps(
                {
                    "sentiment": "neutral",
                    "action_items": [{"id": "../../etc/passwd", "task": "Nasty", "priority": "low"}],
                    "decisions": [],
                    "keywords": [],
                }
            )
        )

    monkeypatch.setattr("backend.routers.intelligence.groq_post", fake_post)
    returned = alice.post(
        "/api/intelligence", json={"transcript_slice": "text", "session_id": session_id}
    ).json()["action_items"][0]["id"]

    assert returned != "../../etc/passwd"
    stored = db_session.query(ActionItem).filter(ActionItem.session_id == session_id).first()
    assert returned == stored.id


# ── Model catalogue ──────────────────────────────────────────────────────────

def test_models_endpoint_lists_only_chat_models(alice, monkeypatch):
    """Groq retires model IDs, and a retired one 404s every request. The
    Settings dropdown is populated from the caller's live account instead."""
    async def fake_get(endpoint, api_key):
        assert endpoint == "/models"
        return {
            "data": [
                {"id": "openai/gpt-oss-120b"},
                {"id": "openai/gpt-oss-20b"},
                {"id": "whisper-large-v3"},
                {"id": "playai-tts"},
                {"id": "meta-llama/llama-guard-4-12b"},
            ]
        }

    monkeypatch.setattr("backend.routers.models.groq_get", fake_get)
    response = alice.get("/api/models")
    assert response.status_code == 200
    body = response.json()
    ids = [m["value"] for m in body["models"]]
    assert ids == ["openai/gpt-oss-120b", "openai/gpt-oss-20b"]
    assert body["defaults"]["chat"] and body["defaults"]["suggestions"]


def test_models_endpoint_requires_authentication(client):
    response = client.get("/api/models", headers={"X-Groq-API-Key": "k"})
    assert response.status_code == 401


def test_models_endpoint_surfaces_a_bad_key_without_echoing_it(alice, monkeypatch):
    async def fake_get(endpoint, api_key):
        raise HTTPException(status_code=401, detail=f"Invalid API Key: {api_key}")

    monkeypatch.setattr("backend.routers.models.groq_get", fake_get)
    response = alice.get("/api/models")
    assert response.status_code == 401
    assert "gsk_test_key_never_persisted" not in response.text
