# Synapse — Complete Technical Deep-Dive (Interview Preparation Guide)

> This document covers every aspect of the Synapse project from first principles — what it is, why it was built the way it was, how every component works, all the architectural and engineering decisions, and the technical workflows from the moment a user clicks "Record" to the moment data is stored in the database. Written to prepare for technical interviews.

---

## Table of Contents

1. [Project Overview & Problem Statement](#1-project-overview--problem-statement)
2. [High-Level Architecture](#2-high-level-architecture)
3. [Technology Stack Rationale](#3-technology-stack-rationale)
4. [Repository Structure Walkthrough](#4-repository-structure-walkthrough)
5. [Backend Deep-Dive](#5-backend-deep-dive)
   - 5.1 [Application Entry Point (main.py)](#51-application-entry-point-mainpy)
   - 5.2 [Database Layer (SQLAlchemy + SQLite)](#52-database-layer-sqlalchemy--sqlite)
   - 5.3 [CRUD Repository Pattern](#53-crud-repository-pattern)
   - 5.4 [API Routers — Every Endpoint Explained](#54-api-routers--every-endpoint-explained)
   - 5.5 [Groq Client Service](#55-groq-client-service)
   - 5.6 [Prompt Engineering & Playbook System](#56-prompt-engineering--playbook-system)
6. [Frontend Deep-Dive](#6-frontend-deep-dive)
   - 6.1 [Session Settings & Storage Engine](#61-session-settings--storage-engine)
   - 6.2 [API Client Layer (api.js)](#62-api-client-layer-apijs)
   - 6.3 [App.jsx — The Master Coordinator](#63-appjsx--the-master-coordinator)
   - 6.4 [TranscriptPanel — Audio & Visualizer](#64-transcriptpanel--audio--visualizer)
   - 6.5 [LiveSuggestionsPanel — Polling Logic](#65-livesuggestionspanel--polling-logic)
   - 6.6 [WorkspacePanel — Chat & Board](#66-workspacepanel--chat--board)
   - 6.7 [HistorySidebar](#67-historysidebar)
   - 6.8 [Navbar — Settings & Playbooks](#68-navbar--settings--playbooks)
7. [End-to-End Technical Workflows](#7-end-to-end-technical-workflows)
   - 7.1 [Audio Recording → Transcript Flow](#71-audio-recording--transcript-flow)
   - 7.2 [Suggestions Generation Flow](#72-suggestions-generation-flow)
   - 7.3 [Intelligence Extraction Flow](#73-intelligence-extraction-flow)
   - 7.4 [Chat Copilot Streaming Flow](#74-chat-copilot-streaming-flow)
   - 7.5 [Session Persistence Flow](#75-session-persistence-flow)
8. [Data Models & Schema Design](#8-data-models--schema-design)
9. [Key Engineering Decisions & Trade-offs](#9-key-engineering-decisions--trade-offs)
10. [Security Architecture](#10-security-architecture)
11. [Error Handling & Resilience](#11-error-handling--resilience)
12. [Likely Interview Questions & Strong Answers](#12-likely-interview-questions--strong-answers)

---

## 1. Project Overview & Problem Statement

### What is Synapse?

Synapse is a **real-time meeting intelligence platform** that runs in the browser. While a meeting is in progress, Synapse:

- **Listens** to live audio via the microphone
- **Transcribes** speech to text in rolling 30-second chunks
- **Generates contextual suggestions** (questions to ask, talking points, fact checks) based on what's being said
- **Extracts structured intelligence** — action items, decisions, sentiment, and keywords — from the conversation
- **Streams an AI assistant** that the user can chat with using the full meeting context
- **Persists everything** to a local SQLite database for post-meeting review

### The Problem It Solves

Traditional meeting tools (Zoom, Google Meet, Teams) either:
1. Record and transcribe AFTER the meeting, making it too late to act on insights
2. Require subscription SaaS plans with recurring costs and cloud data privacy concerns

Synapse solves this by being a **local-first, real-time meeting copilot** — zero SaaS subscription, no cloud data storage, immediate in-meeting value.

### Why This Is a Strong Resume Project

- Demonstrates full-stack ownership (frontend + backend + database + external APIs)
- Uses modern async programming patterns (FastAPI, SSE streaming)
- Integrates AI/ML services (Groq Whisper + LLMs) into a production-style workflow
- Implements a real database schema with relationships and cascade operations
- Shows understanding of browser APIs (MediaRecorder, Web Audio API, Canvas)
- Applies multiple CS fundamentals: streaming protocols, rolling buffers, FFT, prompt engineering

---

## 2. High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                        BROWSER (React SPA)                          │
│                                                                     │
│  ┌─────────────┐  ┌──────────────┐  ┌─────────────┐  ┌─────────┐  │
│  │  Transcript │  │  Suggestions │  │  Workspace  │  │ History │  │
│  │   Panel     │  │    Panel     │  │   Panel     │  │ Sidebar │  │
│  │ (Recording) │  │ (Live cards) │  │(Chat+Board) │  │         │  │
│  └──────┬──────┘  └──────┬───────┘  └──────┬──────┘  └────┬────┘  │
│         │                │                  │              │        │
│         └────────────────┴──────────────────┴──────────────┘        │
│                                    │                                 │
│                              App.jsx (State Hub)                    │
│                                    │                                 │
│                              api.js (HTTP Layer)                    │
└────────────────────────────────────┬────────────────────────────────┘
                                     │  HTTP/SSE (proxied by Vite)
                                     ▼
┌─────────────────────────────────────────────────────────────────────┐
│                      FastAPI Backend (Python)                        │
│                                                                     │
│  /api/transcribe  /api/suggestions  /api/chat  /api/intelligence    │
│  /api/meeting/start  /api/meeting/end  /api/history/*               │
│                                                                     │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │                    SQLAlchemy ORM Layer                      │   │
│  │   MeetingSession → TranscriptEntry, SuggestionItem,         │   │
│  │                    ChatMessage, ActionItem, DecisionItem     │   │
│  └──────────────────────────────┬──────────────────────────────┘   │
│                                 │                                   │
│                          synapse.db (SQLite)                        │
└─────────────────────────────────┬───────────────────────────────────┘
                                  │  HTTPS to Groq Cloud
                                  ▼
┌─────────────────────────────────────────────────────────────────────┐
│                         Groq LPU Cloud                              │
│                                                                     │
│   whisper-large-v3          llama-3.3-70b-versatile                 │
│   (Transcription)           (Suggestions + Intelligence)            │
│                                                                     │
│                         llama-3.1-8b-instant                        │
│                         (Streaming Chat)                            │
└─────────────────────────────────────────────────────────────────────┘
```

**Key architectural choice**: The frontend and backend are completely decoupled. The React SPA communicates with the FastAPI backend exclusively through HTTP REST calls (and SSE for streaming). The Vite development server proxies all `/api/*` requests to `localhost:8000`, which means no CORS issues during development and a clean production deployment path.

---

## 3. Technology Stack Rationale

### Why FastAPI (not Flask, Django, or Express)?

| Criterion | FastAPI | Flask | Django | Express (Node) |
|-----------|---------|-------|--------|----------------|
| Async support | ✅ Native async/await | ❌ Sync (needs workarounds) | ⚠️ Partial | ✅ Native |
| SSE Streaming | ✅ Built-in StreamingResponse | ⚠️ Manual | ⚠️ Manual | ✅ Built-in |
| Auto API docs | ✅ Swagger + ReDoc auto-gen | ❌ Plugin needed | ❌ Plugin needed | ❌ Plugin needed |
| Pydantic validation | ✅ Native | ❌ Manual | ✅ Forms only | ❌ Manual |
| Performance | ✅ Very fast (Starlette base) | ⚠️ Moderate | ⚠️ Moderate | ✅ Fast |

FastAPI was chosen because the backend has **two critical async requirements**:
1. Making non-blocking outbound HTTP calls to Groq (audio transcription + LLM inference)
2. Streaming token-by-token chat responses back to the frontend via SSE

In a synchronous framework like Flask, each request holds a thread. In FastAPI, requests are handled by coroutines on an event loop, so while one request is waiting for Groq to respond, the event loop processes other requests simultaneously.

### Why Groq (not OpenAI or Anthropic)?

- **Speed**: Groq LPUs (Language Processing Units) are purpose-built chips for LLM inference. They deliver 400+ tokens/second vs. ~30-60 from OpenAI's API for GPT-4o.
- **Live meeting use case**: At 30+ tokens/second, the streaming chat response feels instantaneous. At 30-60 tokens/second it feels laggy during a live call.
- **Cost**: Groq has a generous free tier — essential for a demo/portfolio project.
- **Whisper access**: Groq hosts `whisper-large-v3` — the best open-source speech recognition model — via API.

### Why SQLite (not PostgreSQL or MongoDB)?

- **Local-first design**: Synapse runs on your machine. SQLite requires no installation, no server process, and stores all data in a single file (`synapse.db`).
- **Zero-config**: Works immediately after `pip install`.
- **Upgrade path**: SQLAlchemy ORM abstracts the database engine. Switching to PostgreSQL requires only changing one line: `DATABASE_URL = "postgresql://user:pass@host/db"`.
- **MongoDB would be wrong here**: The data is inherently relational. A `MeetingSession` has many `ActionItem`s, many `ChatMessage`s, many `TranscriptEntry`s. Enforcing referential integrity (cascade deletes) is trivial in SQL but complex in MongoDB.

### Why React + Vite (not Next.js or plain HTML)?

- **Vite**: Instant hot module replacement (HMR). Changes reflect in the browser in under 100ms during development.
- **React**: Component-based state management is essential here. The app has 8+ inter-dependent state variables (recording status, transcript entries, suggestion batches, session ID, chat messages, etc.) that multiple components need to read and update. React's unidirectional data flow makes this manageable.
- **Not Next.js**: Next.js adds SSR (server-side rendering) complexity. Since Synapse is a browser-only app (requires mic access, canvas APIs, Web Audio — all unavailable server-side), plain React SPA is the right tool.

### Why Vanilla CSS (not Tailwind)?

- Full control over CSS custom properties (variables). The dark/light theme toggle works by changing a single `data-theme` attribute on `<html>`, which flips ~20 CSS variables simultaneously.
- Glassmorphism effects (`backdrop-filter: blur()`, gradient borders) are easier to express in Vanilla CSS than in Tailwind utility classes.

---

## 4. Repository Structure Walkthrough

```
Synapse/
├── backend/                         # Python FastAPI application
│   ├── database/
│   │   ├── connection.py            # Engine setup, session factory, get_db dependency
│   │   ├── crud.py                  # All database read/write functions (Repository pattern)
│   │   └── models.py                # SQLAlchemy ORM table definitions
│   ├── models/
│   │   └── schemas.py               # Pydantic models (request/response DTOs)
│   ├── prompts/
│   │   └── defaults.py              # All LLM system prompts + model name constants
│   ├── routers/
│   │   ├── transcribe.py            # POST /api/transcribe
│   │   ├── suggestions.py           # POST /api/suggestions
│   │   ├── chat.py                  # POST /api/chat (SSE streaming)
│   │   ├── intelligence.py          # POST /api/intelligence
│   │   ├── meeting.py               # POST /api/meeting/start, /end
│   │   └── history.py               # GET/PUT/DELETE /api/history/*
│   ├── services/
│   │   └── groq_client.py           # Async HTTPX wrapper around Groq's API
│   ├── main.py                      # FastAPI app creation, CORS, router registration
│   └── requirements.txt
├── client/                          # React + Vite SPA
│   ├── src/
│   │   ├── components/
│   │   │   ├── TranscriptPanel.jsx  # Mic controls, audio visualizer, transcript feed
│   │   │   ├── LiveSuggestionsPanel.jsx  # Suggestion batch display + refresh logic
│   │   │   ├── SuggestionCard.jsx   # Individual suggestion card with expand/click
│   │   │   ├── WorkspacePanel.jsx   # Tabbed container: Chat + Action Board
│   │   │   ├── HistorySidebar.jsx   # Past session browser (load/rename/delete)
│   │   │   └── Navbar.jsx           # Brand, playbook switcher, settings modal
│   │   ├── api.js                   # All fetch() calls to backend API
│   │   ├── sessionSettings.js       # sessionStorage read/write + key migration
│   │   ├── App.jsx                  # Master state hub, orchestrates all data flows
│   │   └── styles.css               # Complete CSS design system
│   ├── index.html                   # Entry HTML (Google Fonts loaded here)
│   └── vite.config.js               # Dev server + proxy config
├── synapse.db                       # Auto-generated SQLite database (gitignored)
├── README.md
└── SYSTEM_DESIGN.md
```

---

## 5. Backend Deep-Dive

### 5.1 Application Entry Point (main.py)

```python
@asynccontextmanager
async def lifespan(_: FastAPI):
    create_tables()        # Creates all SQLAlchemy tables if they don't exist
    await get_http_client() # Pre-warms the shared HTTPX async client
    try:
        yield
    finally:
        await close_http_client()  # Gracefully closes connections on shutdown
```

**What `lifespan` does**: FastAPI's `lifespan` context manager replaces the old `@app.on_event("startup")` / `@app.on_event("shutdown")` pattern. It runs setup code before the first request and teardown code after the last one.

**Why pre-warm HTTPX**: Creating an HTTP client on every request adds ~5ms of overhead. By creating one shared client at startup and reusing it, all outbound requests to Groq benefit from connection reuse (HTTP keepalive / connection pooling).

```python
for router in [transcribe.router, suggestions.router, chat.router, 
               meeting.router, history.router, intelligence.router]:
    app.include_router(router, prefix="/api")
    app.include_router(router)  # Also registers without prefix for flexibility
```

**CORS configuration**: `allow_origins=["*"]` is fine for local development but should be locked to specific domains in production to prevent Cross-Site Request Forgery (CSRF).

---

### 5.2 Database Layer (SQLAlchemy + SQLite)

**`connection.py`** sets up three things:

```python
DATABASE_URL = "sqlite:///./synapse.db"

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False},  # SQLite-specific: allows multi-thread access
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()
```

**Why `check_same_thread=False`**: SQLite by default only allows the thread that created the connection to use it. FastAPI runs requests on different threads from a thread pool. This flag disables that restriction, which is safe because SQLAlchemy handles its own connection safety.

**Why `autocommit=False`**: We want explicit transaction control. When we call `db.commit()` in CRUD functions, that's when data is actually written to disk. If an error occurs before commit, the transaction is automatically rolled back.

**The `get_db` dependency**:

```python
def get_db() -> Generator:
    db = SessionLocal()
    try:
        yield db        # Provides the db session to the route handler
    finally:
        db.close()      # Always closes, even if an exception occurred
```

This is FastAPI's **dependency injection** pattern. Any route function that declares `db: Session = Depends(get_db)` automatically gets a fresh, properly managed database session. The `finally` block guarantees the connection is returned to the pool.

---

### 5.3 CRUD Repository Pattern

All database operations are centralized in `crud.py`. No route handler directly queries the database — they always call a CRUD function. This is the **Repository pattern**.

**Why Repository Pattern?**
- Single responsibility: route handlers handle HTTP logic, CRUD handles database logic
- Easy to test: CRUD functions can be unit tested with a test database without touching routes
- Easy to refactor: if switching from SQLite to PostgreSQL, only the engine URL changes, no CRUD functions change

Example — creating a meeting session:
```python
def create_session(db: Session, playbook: str = "general", meeting_memory: str = "") -> MeetingSession:
    session = MeetingSession(playbook=playbook, meeting_memory=meeting_memory)
    db.add(session)    # Stage the INSERT
    db.commit()        # Execute and commit
    db.refresh(session) # Reload from DB to get auto-generated fields (id, started_at)
    return session
```

**Why `db.refresh()`**: After `db.commit()`, SQLAlchemy clears the in-memory representation of the object. `db.refresh()` re-queries the database to get the server-generated values (like the UUID primary key and default timestamps) back into the Python object.

---

### 5.4 API Routers — Every Endpoint Explained

#### `POST /api/transcribe`

```
Client sends: multipart/form-data { audio_file: <WebM binary> }
Header: X-Groq-API-Key: gsk_...
Server does: forward audio to Groq Whisper
Returns: { "text": "transcribed words here" }
```

**Flow**:
1. FastAPI reads the audio bytes from the uploaded file
2. Checks if `audio_bytes` is non-empty (empty recording = skip)
3. Detects the MIME type from the upload (`audio/webm`, `audio/mp4`, etc.)
4. Calls `groq_post_multipart()` which sends a multipart HTTP request to Groq's `/audio/transcriptions` endpoint
5. If Groq returns a 400 (undecodable audio — too short, too quiet), logs a warning and returns `{"text": ""}` silently
6. Returns the transcript text

**Key design decision**: Errors are swallowed and return empty text instead of HTTP 500. This is intentional — a failed transcription chunk should not crash the recording session. The frontend detects empty text and increments a "silence streak" counter instead.

#### `POST /api/suggestions`

This is the most complex endpoint. It has a **3-attempt retry loop with fallback strategies**:

```
Attempt 1: Full context, 600 max tokens, JSON mode
    → If parse fails →
Attempt 2: Shorter prompt, stricter instruction, 450 max tokens
    → If parse fails →  
Attempt 3: Heavily truncated context, 350 max tokens, plain text mode
    → If all fail → HTTP 500
```

**Why three attempts?** LLMs occasionally generate malformed JSON even when instructed not to. Rather than failing loudly, the system degrades gracefully — each attempt is simpler and more constrained than the last.

**Context trimming**:
```python
words = body.transcript_slice.split()[-body.context_window:]
transcript_slice = " ".join(words)
```
Takes only the last N words (default: 800). This keeps the prompt within token limits and ensures suggestions are based on recent conversation, not a 2-hour-old discussion.

**Playbook system**:
```python
playbook_key = (body.playbook or "general").lower()
system_prompt = body.suggestions_prompt or PLAYBOOK_PROMPTS.get(playbook_key, PLAYBOOK_PROMPTS["general"])
```
Custom user prompt overrides the playbook. If no custom prompt, looks up the playbook key in the dictionary. Falls back to "general" if key not found.

#### `POST /api/chat` (SSE Streaming)

This endpoint returns a `StreamingResponse` — instead of waiting for the full LLM response and returning it all at once, it streams each token to the client as it's generated.

```python
async def stream_and_save():
    full_response = []
    async for chunk in iter_groq_chat_stream(x_groq_api_key, payload):
        full_response.append(chunk)
        yield chunk          # Stream to client immediately
    # AFTER streaming completes, reconstruct and save to DB
    if body.session_id:
        token_text = parse_sse_chunks(full_response)
        crud.save_chat_message(db, body.session_id, "assistant", token_text)
```

**Why save after streaming?** The full message isn't available until all tokens have been streamed. By collecting chunks in `full_response` and parsing them after the stream completes, we save exactly what the user saw — no truncation, no partial saves.

**Two chat modes**:
- `mode="suggestion"`: Uses the "detail" prompt template (focused on expanding a suggestion with practical action steps)
- `mode="chat"`: Uses the general "copilot" prompt template (treats it as a freeform conversation)

#### `POST /api/intelligence`

Runs structured NLP extraction on the transcript every ~2 chunks. Returns:
- `sentiment`: "positive" | "neutral" | "constructive" | "conflicted"
- `action_items`: list of `{task, assignee, priority}` objects
- `decisions`: list of decision strings
- `keywords`: list of topic strings

Uses `response_format={"type": "json_object"}` — this is Groq's JSON mode, which forces the LLM to always return valid JSON. The model is `llama-3.3-70b-versatile` at `temperature=0.1` (very low — we want deterministic structured extraction, not creative generation).

---

### 5.5 Groq Client Service

`groq_client.py` is a thin wrapper around HTTPX that handles the authentication header and error mapping:

```python
async def groq_post(endpoint: str, api_key: str, payload: dict) -> dict:
    client = await get_http_client()
    response = await client.post(
        f"https://api.groq.com/openai/v1{endpoint}",
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        json=payload,
    )
    if response.status_code != 200:
        raise HTTPException(status_code=response.status_code, detail=response.text)
    return response.json()
```

**Key pattern**: Non-200 responses are converted to FastAPI `HTTPException`, which the route handlers can catch and re-raise or handle gracefully.

For streaming (`iter_groq_chat_stream`):
```python
async with client.stream("POST", url, ...) as response:
    async for line in response.aiter_lines():
        if line.startswith("data: "):
            yield f"{line}\n\n"
```

This is an **async generator** — it `yield`s each SSE line as it arrives from Groq, which FastAPI's `StreamingResponse` then immediately forwards to the browser client.

---

### 5.6 Prompt Engineering & Playbook System

All prompts live in `defaults.py`. This is an important design decision — centralized prompts are easy to version, test, and update.

**Playbook prompts** enforce a strict JSON schema in the system message:
```
Return only valid JSON with this exact shape:
{"suggestions":[{"type":"ANSWER","title":"Short title","preview":"Useful preview"}]}
```

The allowed suggestion types (`QUESTION_TO_ASK`, `TALKING_POINT`, `ANSWER`, `FACT_CHECK`, `CLARIFICATION`) act as a controlled vocabulary — the LLM can't generate arbitrary suggestion types.

**Intelligence prompt** uses XML-style tags for structure:
```
You are a meeting intelligence engine. Return ONLY valid JSON:
{
  "sentiment": "positive" | "neutral" | "constructive" | "conflicted",
  "action_items": [{"task": "string", "assignee": "string or null", "priority": "high|medium|low"}],
  "decisions": ["string"],
  "keywords": ["string"]
}
```

**Why XML tags in prompts?** Research from Anthropic and others shows LLMs respond more reliably to explicitly tagged context blocks. The `<transcript>`, `<meeting_memory>`, `<previous_suggestions>` tags help the model clearly identify what each piece of context is.

---

## 6. Frontend Deep-Dive

### 6.1 Session Settings & Storage Engine

All user configuration (API key, model choice, playbook, context window sizes) lives in `sessionSettings.js`. Settings are stored in `sessionStorage` under the key `synapse_session_settings`.

**Why `sessionStorage` and not `localStorage`?**
- `sessionStorage` is tab-scoped and cleared when the tab is closed
- The API key is the most sensitive piece of data in the app
- If stored in `localStorage`, it persists indefinitely — a security risk on shared computers
- `sessionStorage` means the key is cleared at end of session (natural for meeting context)

**Migration logic**: When the project was renamed from MeetScribe to Synapse, the storage key changed. Rather than losing existing users' settings:

```javascript
export function loadSessionSettings() {
  let raw = sessionStorage.getItem('synapse_session_settings');
  if (!raw) {
    const oldRaw = sessionStorage.getItem('meetscribe_session_settings');
    if (oldRaw) {
      // Migrate: read old key, write to new key
      const normalized = normalizeSessionSettings(JSON.parse(oldRaw));
      sessionStorage.setItem('synapse_session_settings', JSON.stringify(normalized));
      return normalized;
    }
    return { ...DEFAULT_SESSION_SETTINGS };
  }
  return normalizeSessionSettings(JSON.parse(raw));
}
```

**`normalizeSessionSettings`** enforces type safety. Even if the stored JSON has corrupt or missing fields (e.g., someone manually edited it), normalization fills in defaults and coerces types:
```javascript
suggestionsContextWindow: parseInteger(settings?.suggestionsContextWindow, 800)
```

---

### 6.2 API Client Layer (api.js)

Every backend call goes through `api.js`. This provides:

1. **Centralized base URL**: `const API_BASE = import.meta.env.VITE_API_BASE || '/api'` — reads from environment variable in production, defaults to Vite proxy in dev.

2. **Automatic API key injection**: Every request builder calls `getGroqApiKey()` which reads from `sessionStorage` and injects it into the `X-Groq-API-Key` header.

3. **SSE stream decoder**: The `streamChat()` function reads the `ReadableStream` byte-by-byte, splits on `\n\n` SSE boundaries, extracts `data:` payloads, and calls `onToken(token)` for each token received.

```javascript
const reader = response.body.getReader();
const decoder = new TextDecoder();
let buffer = '';
while (true) {
  const { done, value } = await reader.read();
  if (done) break;
  buffer += decoder.decode(value, { stream: true });
  const chunks = buffer.split('\n\n');
  buffer = chunks.pop() || '';  // Keep incomplete chunk in buffer
  for (const chunk of chunks) {
    if (!chunk.startsWith('data: ')) continue;
    const token = JSON.parse(chunk.slice(6)).choices?.[0]?.delta?.content;
    if (token) onToken(token);
  }
}
```

**Why the buffer?** Network packets don't align with SSE event boundaries. A single `read()` call might return half an SSE event, or two events combined. The buffer accumulates bytes until a full `\n\n`-terminated event is available.

---

### 6.3 App.jsx — The Master Coordinator

`App.jsx` is the single source of truth for all application state. It owns:

| State Variable | Type | Purpose |
|---|---|---|
| `settings` | Object | All user settings (API key, model, playbook) |
| `transcriptEntries` | Array | Timestamped transcript entries (speech + silence) |
| `suggestionBatches` | Array | Groups of suggestions, newest first |
| `chatMessages` | Array | Full in-session chat history |
| `isRecording` | Boolean | Whether mic is active |
| `sessionId` | String/null | Current meeting's database UUID |
| `actionItems` | Array | Extracted tasks from intelligence |
| `decisions` | Array | Extracted decisions from intelligence |
| `sentiment` | String | Current meeting sentiment |
| `keywords` | Array | Current keyword list |

**The intelligence polling throttle**:
```javascript
useEffect(() => {
  // Run intelligence analysis every 2 new transcript chunks
  if (transcriptEntries.length > 0 && transcriptEntries.length % 2 === 0) {
    runIntelligence(spokenTranscript);
  }
}, [transcriptEntries.length]);
```

**Why every 2 chunks?** Intelligence extraction makes an LLM API call. Running it every single chunk (every 30 seconds) would be wasteful and potentially hit rate limits. Every 2 chunks = every ~60 seconds of speech is a reasonable cadence.

**The `spokenTranscript` memoization**:
```javascript
const spokenTranscript = useMemo(
  () => transcriptEntries.filter(e => e.kind !== 'silence').map(e => e.text).join(' '),
  [transcriptEntries]
);
```

Filters out `[Silence for Xs]` entries before sending to intelligence analysis. Silence text doesn't add semantic value and wastes tokens.

---

### 6.4 TranscriptPanel — Audio & Visualizer

This component handles two independent concerns:
1. **Audio recording** using `MediaRecorder` API
2. **Frequency visualization** using Web Audio API + Canvas

#### The Rolling Segment Strategy

Instead of one long recording, audio is captured in 30-second "segments":

```javascript
const startRecorderSegment = (stream) => {
  const recorder = new MediaRecorder(stream, { mimeType });
  segmentChunksRef.current = [];
  
  recorder.ondataavailable = (e) => {
    if (e.data?.size > 0) segmentChunksRef.current.push(e.data);
  };
  
  recorder.onstop = async () => {
    // Package collected chunks into a blob
    const blob = new Blob(segmentChunksRef.current, { type: mimeType });
    segmentChunksRef.current = [];
    // Transcribe and immediately start next segment
    await sendSegmentForTranscription(blob);
    if (isRecordingRef.current && streamRef.current) {
      startRecorderSegment(streamRef.current); // Recurse!
    }
  };
  
  recorder.start(1000); // Fire ondataavailable every 1 second
  segmentTimeoutRef.current = setTimeout(() => recorder.stop(), 30000);
};
```

**Why 30 seconds?** It's the Goldilocks interval:
- Too short (5s): Too much transcription API overhead, audio segments too small to capture meaningful context
- Too long (120s): User waits 2 minutes for first suggestions; app feels unresponsive
- 30s: Fast enough to feel live, long enough for meaningful speech chunks

**Why `recorder.start(1000)`?** The `1000ms` argument means `ondataavailable` fires every 1 second, accumulating audio data progressively. Without this, `ondataavailable` only fires when `recorder.stop()` is called, meaning a network interruption would lose the entire 30 seconds of audio.

#### Canvas Audio Visualizer

```javascript
const audioCtx = new AudioContext();
const analyser = audioCtx.createAnalyser();
analyser.fftSize = 256;           // 256-point FFT = 128 frequency bins
const source = audioCtx.createMediaStreamSource(stream);
source.connect(analyser);

const draw = () => {
  requestAnimationFrame(draw);  // ~60fps rendering
  analyser.getByteFrequencyData(dataArray);  // 0-255 amplitude per bin
  // Draw bars on canvas using the frequency data
};
```

**FFT (Fast Fourier Transform)**: The raw audio waveform is a time-domain signal (amplitude over time). FFT converts it to a frequency-domain signal (amplitude per frequency). This lets us draw a bar chart where each bar represents a frequency range (bass on the left, treble on the right).

**`fftSize=256`**: Produces 128 frequency bins. More bins = more detail but more computation. 128 bins gives a clean looking visualizer without being wasteful.

**Why Canvas, not DOM/CSS?**: Canvas drawing bypasses React's Virtual DOM reconciliation entirely. At 60fps, re-rendering 128 bars as DOM elements would be extremely slow. Canvas updates don't trigger layout reflows or style recalculations.

---

### 6.5 LiveSuggestionsPanel — Polling Logic

Suggestions are fetched reactively — `App.jsx` sends a "refresh request" (a token + source label) to this component via props. The component watches the token and fires the API call:

```javascript
useEffect(() => {
  if (!refreshRequest.token || !settings.apiKey) return;
  const key = `${refreshRequest.token}-${refreshRequest.source}`;
  if (completedRequests.has(key) || inFlightRef.current === key) return;
  inFlightRef.current = key;
  // Fetch suggestions...
}, [refreshRequest]);
```

**Deduplication logic**: `completedRequests` (a Set) tracks every request that has been processed. `inFlightRef` tracks the currently pending request. This prevents the same transcript state from triggering duplicate API calls even if the component re-renders multiple times.

**Three refresh triggers** (from `App.jsx`):
1. `source: 'auto'` — triggered by each new transcript chunk
2. `source: 'manual'` — triggered by the user clicking "Refresh"
3. `source: 'silence'` — triggered when silence streak hits 1 or multiples of 3

---

### 6.6 WorkspacePanel — Chat & Board

This component contains two tabs:
1. **Chat Tab**: Renders chat message history and handles user input. Calls `streamChat()` from `api.js` and uses `onToken` callback to append tokens to the assistant's message one at a time (streaming effect).
2. **Board Tab**: Renders `actionItems`, `decisions`, `sentiment`, and `keywords` passed down from `App.jsx`. Provides UI for marking action items complete/incomplete and deleting them.

---

### 6.7 HistorySidebar

Fetches past sessions from `GET /api/history` on mount and displays them. Allows:
- **Loading** a past session (calls `GET /api/history/{session_id}` to get full detail)
- **Renaming** (calls `PUT /api/history/{session_id}/title`)
- **Deleting** (calls `DELETE /api/history/{session_id}`)

---

### 6.8 Navbar — Settings & Playbooks

Contains the Settings modal which reads/writes `sessionSettings`. Playbook buttons use immediate-action updates: clicking a playbook immediately calls `onSaveSettings({ ...settings, playbook: newValue })`, which updates `sessionStorage` and triggers React re-render with the new playbook, affecting the next suggestions request.

---

## 7. End-to-End Technical Workflows

### 7.1 Audio Recording → Transcript Flow

```
1. User clicks mic button
   → App calls navigator.mediaDevices.getUserMedia({ audio: true })
   → Browser shows permission prompt
   → Returns a MediaStream object

2. TranscriptPanel creates AudioContext
   → Connects MediaStream to AnalyserNode
   → Starts requestAnimationFrame drawing loop for visualizer

3. TranscriptPanel creates MediaRecorder
   → Starts recording (ondataavailable fires every 1 second)
   → Sets 30-second timeout

4. After 30 seconds (or manual flush):
   → MediaRecorder.stop() called
   → ondataavailable fires one final time
   → onstop fires with all collected chunks
   → Chunks packaged into WebM Blob (~30–120KB typical)

5. POST /api/transcribe with Blob
   → FastAPI reads bytes from multipart upload
   → HTTPX sends to Groq: POST https://api.groq.com/openai/v1/audio/transcriptions
   → Groq Whisper processes and returns JSON: {"text": "..."}

6. Response returns to TranscriptPanel
   → Empty text → silence streak increments
   → Non-empty text → onTranscriptChunk(text) called

7. App.jsx handles onTranscriptChunk:
   → Appends {time, text, kind: 'speech'} to transcriptEntries state
   → Sets refreshRequest with new token (triggers suggestions)
   → Checks if intelligence run needed (every 2 chunks)

8. TranscriptPanel starts next segment immediately (recurse)
```

### 7.2 Suggestions Generation Flow

```
1. App.jsx sets refreshRequest = { token: Date.now(), source: 'auto' }

2. LiveSuggestionsPanel useEffect fires (watches refreshRequest)
   → Checks deduplication: token already processed? → skip
   → Sets inFlightRef to this request key

3. POST /api/suggestions with:
   - transcript_slice: last 800 words of spoken transcript
   - playbook: "design" (or whatever's active)
   - previous_suggestions: last 6 suggestion titles
   - session_id: current meeting UUID
   - model: "llama-3.3-70b-versatile"
   
4. Backend builds user message with XML-tagged context blocks
   
5. Request sent to Groq chat completions API with:
   - response_format: { type: "json_object" }
   - temperature: 0.2 (low — deterministic suggestions)
   - system prompt from PLAYBOOK_PROMPTS["design"]

6. Groq returns JSON string: 
   {"suggestions": [{"type": "FACT_CHECK", "title": "...", "preview": "..."}, ...]}

7. Backend parses response, validates exactly 3 suggestions
   → If valid: saves to DB (suggestion_items table), returns to client
   → If invalid: retries with progressively simpler context

8. LiveSuggestionsPanel receives response
   → Prepends new batch to suggestionBatches state
   → Renders new SuggestionCard components
   → Adds token to completedRequests Set
```

### 7.3 Intelligence Extraction Flow

```
1. App.jsx triggers runIntelligence(spokenTranscript) every 2 chunks

2. Guards:
   - No API key? → return
   - Transcript empty? → return
   - Fewer than 20 words? → return (not enough content to analyze)

3. POST /api/intelligence with:
   - transcript_slice: full spoken transcript
   - context_window: 1000 words
   - session_id: current session UUID
   - model: "llama-3.3-70b-versatile"

4. Backend trims to last 1000 words
   Builds prompt → Groq chat completions with JSON mode
   
5. Groq returns structured JSON:
   {
     "sentiment": "positive",
     "action_items": [{"task": "...", "assignee": "Sarah", "priority": "high"}],
     "decisions": ["Use React for the frontend"],
     "keywords": ["authentication", "deployment", "timeline"]
   }

6. Backend persists to DB:
   - Each action_item → INSERT into action_items table
   - Each decision → INSERT into decision_items table

7. App.jsx receives response:
   - Updates sentiment state
   - Merges new action_items (dedup by task text)
   - Merges new decisions (dedup by content)
   - Updates keywords

8. WorkspacePanel Board tab re-renders with new data
```

### 7.4 Chat Copilot Streaming Flow

```
1. User types message in WorkspacePanel or clicks a suggestion card

2. streamChat() called in api.js:
   POST /api/chat with:
   - message: user's text
   - history: all prior messages this session
   - full_transcript: entire spoken transcript
   - mode: "chat" or "suggestion"
   - session_id: current UUID

3. Backend selects prompt template (detail or copilot)
   → Fills {{FULL_TRANSCRIPT}} placeholder
   → Builds messages array: [system, ...history, {role:"user", content:message}]
   → Saves user message to DB immediately

4. Backend calls iter_groq_chat_stream() — async generator
   → Opens streaming HTTP connection to Groq
   → Groq starts generating tokens

5. FastAPI StreamingResponse wraps stream_and_save() generator:
   → Each token chunk arrives from Groq
   → Full response string accumulated in memory
   → Each chunk immediately yielded to FastAPI
   → FastAPI immediately writes chunk to HTTP response

6. Browser receives SSE chunks:
   data: {"choices": [{"delta": {"content": "The"}}]}
   data: {"choices": [{"delta": {"content": " login"}}]}
   ...
   data: [DONE]

7. api.js streamChat() calls onToken(token) for each token
   → WorkspacePanel appends token to last chat message
   → React re-renders chat bubble with updated text (streaming effect)

8. After [DONE]: backend extracts full text from accumulated chunks
   → Saves assistant message to DB (chat_messages table)
```

### 7.5 Session Persistence Flow

```
Start of meeting:
  POST /api/meeting/start
  → Creates MeetingSession row with UUID, playbook, memory, status="active"
  → Returns session_id to client
  → Client stores session_id in React state

During meeting:
  - Suggestions → saved to suggestion_items (if session_id present)
  - Chat messages → saved to chat_messages (both user + assistant)
  - Action items → saved to action_items (from intelligence)
  - Decisions → saved to decision_items (from intelligence)
  (Transcript entries are NOT automatically saved — only on explicit end)

End of meeting:
  POST /api/meeting/end
  → Updates MeetingSession: ended_at=now(), status="ended"

History retrieval:
  GET /api/history → list of all sessions (summary)
  GET /api/history/{id} → full session detail with all related records
```

---

## 8. Data Models & Schema Design

### Entity Relationship Overview

```
MeetingSession (1)
    ├── TranscriptEntry (many)   kind: "speech" | "silence"
    ├── SuggestionItem  (many)   type: "TALKING_POINT" | "ANSWER" | etc.
    ├── ChatMessage     (many)   role: "user" | "assistant"
    ├── ActionItem      (many)   priority: "high"|"medium"|"low", status: "pending"|"completed"
    └── DecisionItem    (many)   plain content string
```

### Primary Key Strategy

All primary keys are **UUID strings** (not auto-increment integers):
```python
id = Column(String, primary_key=True, default=_uuid)
def _uuid():
    return str(uuid.uuid4())
```

**Why UUIDs over auto-increment?**
- Globally unique — if the app ever syncs to a cloud database or merges multiple local databases, there are no ID conflicts
- IDs are safe to expose in URLs (`/api/history/4a1b2c3d-...`) — sequential integers reveal business data (how many records exist)
- UUIDs can be generated client-side without a database round-trip

### Cascade Deletes

```python
transcript_entries = relationship("TranscriptEntry", cascade="all, delete-orphan")
```

When a `MeetingSession` is deleted, SQLAlchemy automatically deletes all associated `TranscriptEntry`, `SuggestionItem`, `ChatMessage`, `ActionItem`, and `DecisionItem` records. No manual cleanup required.

---

## 9. Key Engineering Decisions & Trade-offs

### Decision 1: Client-Side API Key vs. Server-Side Environment Variable

**Chosen**: Client-side (`sessionStorage`), sent in `X-Groq-API-Key` header

**Trade-off**:
- ✅ Pro: No server configuration needed — zero setup friction
- ✅ Pro: Key never stored on server disk — reduces attack surface
- ✅ Pro: Each user brings their own key — scales to many users without cost
- ❌ Con: Key visible in browser memory (though sessionStorage is not accessible to other tabs or external scripts)
- ❌ Con: Key transmitted over HTTP on each request (acceptable when using HTTPS in production)

### Decision 2: Rolling 30-Second Segments vs. Continuous Streaming

**Chosen**: Rolling 30-second segments (chunked HTTP uploads)

**Trade-off**:
- ✅ Pro: Simple to implement — standard REST API calls
- ✅ Pro: Works with any backend (no WebSocket complexity)
- ✅ Pro: Each chunk is independent — a network failure doesn't lose everything
- ❌ Con: 30-second delay before first suggestions after recording starts
- ❌ Con: Can't do word-by-word real-time transcription

**Alternative (production-grade)**: WebSocket connection streaming audio in 200ms chunks to a real-time ASR service (Deepgram, AssemblyAI). Would give sub-second word-level transcription.

### Decision 3: Local SQLite vs. Cloud Database

**Chosen**: Local SQLite

**Trade-off**:
- ✅ Pro: Zero configuration, works offline, no cloud dependency
- ✅ Pro: Meetings stay private on user's machine
- ❌ Con: Single-user only — can't sync across devices
- ❌ Con: No concurrent write safety for multiple simultaneous users

**Upgrade path**: Change `DATABASE_URL = "postgresql://..."` — all SQLAlchemy ORM code works unchanged.

### Decision 4: Context Window Trimming

Instead of sending the full transcript to every LLM call, only the last N words are sent:

```python
words = body.transcript_slice.split()[-body.context_window:]
```

**Why**: LLMs have token limits (Llama 3.3 70B: 128K tokens). For a 3-hour meeting at 150 WPM, the full transcript is ~27,000 words — comfortably within limits but wasteful and expensive. Recent context (last 800 words = ~last 5 minutes of speech) is what drives relevant suggestions.

---

## 10. Security Architecture

### Threat Model & Mitigations

| Threat | Mitigation |
|--------|-----------|
| API key theft from client | sessionStorage (tab-isolated), cleared on tab close |
| Man-in-the-middle API key interception | HTTPS in production (TLS 1.3) |
| SQL injection | SQLAlchemy parameter binding (never raw SQL string formatting) |
| Cross-site request forgery | sessionStorage not accessible cross-origin (unlike cookies) |
| XSS stealing sessionStorage | React's JSX auto-escapes all user content by default |
| Unrestricted API access | CORS configured (lock `allow_origins` in production) |

### API Key Flow

```
Browser sessionStorage
    → JavaScript reads key
    → Adds to HTTP header: X-Groq-API-Key: gsk_...
    → Vite proxies request to FastAPI (HTTPS in prod)
    → FastAPI extracts header, passes directly to Groq
    → Key NEVER written to disk on backend
```

---

## 11. Error Handling & Resilience

### Frontend Resilience

| Scenario | Behavior |
|----------|----------|
| API key not set | Recording starts, transcription silently returns empty strings, suggestions show "Add API key" |
| Backend server down | ECONNREFUSED → caught in api.js → error state shown in panel |
| Empty audio chunk | Returns `{text: ""}`, client increments silence streak counter |
| Mic permission denied | Caught in `getUserMedia` catch block, status text updated |
| LLM returns bad JSON | 3-attempt retry with fallback strategies |
| Tab closed mid-meeting | sessionStorage cleared, meeting session left as "active" in DB |

### Backend Resilience

```python
# Transcription: graceful empty response on audio decode failure
except HTTPException as exc:
    if exc.status_code == 400 and "could not process file" in str(exc.detail):
        logger.warning("Skipping undecodable audio chunk")
    return {"text": ""}

# Suggestions: 3-attempt retry ladder
for attempt in attempts:
    try:
        result = await groq_post(...)
        suggestions = _parse_suggestions(raw)
        return SuggestionsResponse(suggestions=suggestions)
    except Exception as exc:
        last_error = exc
        continue  # Try next attempt

raise HTTPException(status_code=500, ...) from last_error
```

---

## 12. Likely Interview Questions & Strong Answers

**Q: "Why did you use FastAPI instead of Flask?"**

> FastAPI is built on Starlette which runs on Python's asyncio event loop. For Synapse, I needed two async capabilities: non-blocking outbound HTTP calls to Groq (so one request waiting on Groq doesn't block other users), and true SSE streaming for the chat feature. Flask is synchronous by default — I'd need Flask 2.0+ with async support, which adds complexity. FastAPI also gives me automatic Pydantic validation and Swagger UI documentation out of the box, which matters for maintainability.

**Q: "How does the audio streaming work?"**

> The browser uses the MediaRecorder API to capture mic audio in WebM format. I record in 30-second rolling segments — `recorder.start(1000)` fires `ondataavailable` every second to accumulate audio buffers. After 30 seconds, `recorder.stop()` fires the `onstop` callback which packages everything into a Blob and uploads it to `/api/transcribe`. The backend forwards it to Groq's Whisper API and returns the transcript. Then immediately starts the next 30-second segment. It's like a relay race — one segment ends exactly as the next begins.

**Q: "What is the Repository Pattern and why did you use it?"**

> The Repository Pattern is where all database access is centralized in a separate module (crud.py in this case). Route handlers never query the database directly — they call CRUD functions. This separates concerns: routes handle HTTP logic, CRUD handles data logic. Benefits: easier to unit test CRUD in isolation, easier to change the database engine (only connection.py changes, not crud.py), and easier to audit all database operations in one file.

**Q: "What's the difference between sessionStorage and localStorage?"**

> Both are browser key-value stores. `localStorage` persists until explicitly cleared — it survives tab closes, browser restarts, even reboots. `sessionStorage` is tab-scoped and cleared when the tab is closed. I chose `sessionStorage` for the Groq API key because it's more secure — if someone walks away from an unlocked computer, closing the browser tab automatically clears the key. It also makes sense semantically: the API key is only needed for the current meeting session.

**Q: "How does Server-Sent Events work in your chat feature?"**

> SSE is a unidirectional streaming protocol over HTTP. The client makes one POST request, and the server keeps the connection open and writes chunks of data. Each chunk is formatted as `data: {json}\n\n`. The browser's `response.body.getReader()` lets me read the stream byte-by-byte as data arrives. I collect each token and append it to the chat message in React state, which gives the streaming typewriter effect. The key difference from WebSockets is SSE is one-directional (server to client only) and simpler to implement over standard HTTP.

**Q: "How do you handle LLM hallucinations or malformed JSON?"**

> For suggestions, I have a 3-attempt retry loop. Attempt 1 sends the full context with JSON mode enabled. If parsing fails, Attempt 2 sends a stricter instruction ("your previous answer was invalid"). If that fails, Attempt 3 strips context down to bare minimum. Only if all three fail does the endpoint return HTTP 500. For intelligence extraction, I catch JSON parse exceptions, log them as warnings, and return an empty fallback object — so the UI doesn't crash, it just doesn't update. This degrades gracefully rather than failing loudly.

**Q: "How would you scale this to handle thousands of users?"**

> Several changes: First, swap SQLite for PostgreSQL (just a DATABASE_URL change in SQLAlchemy). Second, deploy FastAPI behind a process manager like Gunicorn with multiple uvicorn workers — or containerize with Docker and scale horizontally. Third, the current API key model (users bring their own key) already scales infinitely since each user's requests are billed to their own Groq account. Fourth, for real-time transcription at scale, replace the 30-second chunk polling with WebSockets streaming to Deepgram or AssemblyAI. Fifth, add Redis for caching frequently accessed session summaries.
