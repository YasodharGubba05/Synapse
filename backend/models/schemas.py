from typing import Literal, Optional, List

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator


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
    # Absent when the model first produces the item; populated with the
    # database id once it is persisted, so the client can update and
    # complete it later instead of holding a throwaway local id.
    id: Optional[str] = None
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
    title: str = Field(min_length=1, max_length=300)


class TranscriptEntryRequest(BaseModel):
    """One captured transcript segment, persisted against its meeting."""

    text: str = Field(min_length=1, max_length=20000)
    time: Optional[str] = Field(default=None, max_length=32)
    isoTime: Optional[str] = Field(default=None, max_length=64)
    kind: Literal["speech", "silence"] = "speech"


# ── Action Item CRUD ──────────────────────────────────────────────────────────

class ActionItemStatusRequest(BaseModel):
    status: Literal["pending", "completed"]


# ── Authentication ────────────────────────────────────────────────────────────

MIN_PASSWORD_LENGTH = 10
MAX_PASSWORD_LENGTH = 128


def _validate_password_strength(value: str) -> str:
    if len(value) < MIN_PASSWORD_LENGTH:
        raise ValueError(f"Password must be at least {MIN_PASSWORD_LENGTH} characters long")
    if len(value) > MAX_PASSWORD_LENGTH:
        raise ValueError(f"Password must be at most {MAX_PASSWORD_LENGTH} characters long")
    if not any(ch.isalpha() for ch in value):
        raise ValueError("Password must contain at least one letter")
    if not any(ch.isdigit() for ch in value):
        raise ValueError("Password must contain at least one number")
    if value.strip() != value:
        raise ValueError("Password must not start or end with whitespace")
    return value


class RegisterRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=False)

    email: EmailStr
    password: str
    full_name: Optional[str] = Field(default=None, max_length=120)

    @field_validator("password")
    @classmethod
    def check_password(cls, value: str) -> str:
        return _validate_password_strength(value)

    @field_validator("full_name")
    @classmethod
    def clean_full_name(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return None
        cleaned = value.strip()
        return cleaned or None


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=MAX_PASSWORD_LENGTH)


class PasswordChangeRequest(BaseModel):
    current_password: str = Field(min_length=1, max_length=MAX_PASSWORD_LENGTH)
    new_password: str

    @field_validator("new_password")
    @classmethod
    def check_password(cls, value: str) -> str:
        return _validate_password_strength(value)


class UserResponse(BaseModel):
    id: str
    email: str
    full_name: Optional[str] = None
    created_at: Optional[str] = None


class AuthResponse(BaseModel):
    user: UserResponse
    expires_in: int
