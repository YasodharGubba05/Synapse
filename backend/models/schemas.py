from typing import Literal, Optional, List

from pydantic import BaseModel, Field


# ── Suggestions ───────────────────────────────────────────────────────────────

class SuggestionRequest(BaseModel):
    transcript_slice: str
    latest_transcript_chunk: Optional[str] = None
    meeting_memory: Optional[str] = None
    previous_suggestions: List[str] = Field(default_factory=list)
    silence_streak_count: int = 0
    suggestions_prompt: Optional[str] = None
    context_window: int = 800
    session_id: Optional[str] = None
    model: Optional[str] = None
    playbook: Optional[str] = "general"


class Suggestion(BaseModel):
    type: Literal[
        "QUESTION_TO_ASK",
        "TALKING_POINT",
        "ANSWER",
        "FACT_CHECK",
        "CLARIFICATION",
    ]
    title: str
    preview: str


class SuggestionsResponse(BaseModel):
    suggestions: List[Suggestion]


# ── Chat ──────────────────────────────────────────────────────────────────────

class ChatMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str


class ChatRequest(BaseModel):
    message: str
    history: List[ChatMessage] = Field(default_factory=list)
    full_transcript: str
    meeting_memory: Optional[str] = None
    mode: Literal["chat", "suggestion"] = "chat"
    chat_prompt: Optional[str] = None
    detail_prompt: Optional[str] = None
    context_window: int = 3000
    session_id: Optional[str] = None
    model: Optional[str] = None


# ── Intelligence ──────────────────────────────────────────────────────────────

class IntelligenceRequest(BaseModel):
    transcript_slice: str
    playbook: Optional[str] = "general"
    context_window: int = 1200
    session_id: Optional[str] = None
    model: Optional[str] = None


class ActionItemSchema(BaseModel):
    task: str
    assignee: Optional[str] = None
    priority: Literal["high", "medium", "low"] = "medium"


class IntelligenceResponse(BaseModel):
    sentiment: Literal["positive", "neutral", "constructive", "conflicted"]
    action_items: List[ActionItemSchema]
    decisions: List[str]
    keywords: List[str]


# ── Meeting ───────────────────────────────────────────────────────────────────

class MeetingStartRequest(BaseModel):
    meeting_memory: Optional[str] = None
    playbook: Optional[str] = "general"
    title: Optional[str] = "Untitled Meeting"


class MeetingStartResponse(BaseModel):
    session_id: str
    started_at: str
    status: str


class MeetingEndRequest(BaseModel):
    session_id: str


class MeetingEndResponse(BaseModel):
    session_id: str
    ended_at: str
    status: str


# ── History ───────────────────────────────────────────────────────────────────

class SessionSummary(BaseModel):
    id: str
    title: str
    playbook: str
    started_at: str
    ended_at: Optional[str]
    status: str
    transcript_count: int
    action_item_count: int


class SessionDetail(BaseModel):
    id: str
    title: str
    playbook: str
    started_at: str
    ended_at: Optional[str]
    status: str
    meeting_memory: str
    transcript_entries: list
    suggestions: list
    chat_messages: list
    action_items: list
    decisions: list


class UpdateTitleRequest(BaseModel):
    title: str


# ── Action Item CRUD ──────────────────────────────────────────────────────────

class ActionItemStatusRequest(BaseModel):
    status: Literal["pending", "completed"]
