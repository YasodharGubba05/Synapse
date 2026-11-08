# Synapse — Real-Time Meeting Intelligence Platform

[![FastAPI](https://img.shields.io/badge/FastAPI-009688?style=for-the-badge&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![React](https://img.shields.io/badge/React-20232A?style=for-the-badge&logo=react&logoColor=61DAFB)](https://react.dev)
[![Groq LPU](https://img.shields.io/badge/Groq_LPU-F55C5C?style=for-the-badge&logo=openai&logoColor=white)](https://groq.com)
[![SQLite](https://img.shields.io/badge/SQLite-07405E?style=for-the-badge&logo=sqlite&logoColor=white)](https://sqlite.org)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-4169E1?style=for-the-badge&logo=postgresql&logoColor=white)](https://postgresql.org)
[![Python](https://img.shields.io/badge/Python_3.10+-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://python.org)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg?style=for-the-badge)](https://opensource.org/licenses/MIT)

Synapse is an enterprise-grade, real-time meeting copilot and intelligence platform. It ingests live audio streams from your browser, transcribes them in rolling segments, executes periodic natural language processing (NLP) to extract tasks and decisions, visualizes conversational sentiment, and features a context-aware AI assistant.

Built on a decoupled architecture, Synapse combines a **FastAPI asynchronous backend**, **Groq's LPU (Language Processing Unit) inference cloud**, a **React 19 single-page client**, and a **SQLAlchemy ORM layer** backed by SQLite locally and managed PostgreSQL in production.

Every account is isolated: a user only ever sees their own meetings, transcripts, chat threads, suggestions, decisions and action items, enforced in the backend on every request.

---

## Key Capabilities

*   **🎙️ Asynchronous Audio Chunking Pipeline**: Ingests rolling 30-second audio segments from the client browser using the Web MediaStream and MediaRecorder APIs. This keeps latency minimal and protects against network-related data loss.
*   **📊 Canvas-Based Audio Visualizer**: Renders real-time mic frequency data using the Web Audio API (`AnalyserNode` with Fast Fourier Transforms) directly to an HTML5 Canvas, eliminating layout reflows and reducing CPU overhead.
*   **🎯 Scenario-Specific Playbooks**: Features hot-swappable suggestion models tailored for common business meetings (General Meeting, Daily Standup, Product Design, Sales Discovery).
*   **📋 Structured Workspace Boards**: Automatically extracts action items (categorized by assignee and High/Medium/Low priority) and log decisions. Tracks and updates action statuses (pending/completed) directly in the database.
*   **📈 Real-Time Sentiment & Keywords**: Visualizes ongoing meeting sentiment (Positive, Constructive, Neutral, Conflicted) and maps core keywords.
*   **🔐 Account-Isolated Workspaces**: Argon2id password hashing, HTTP-only cookie sessions with rotating refresh tokens, CSRF protection and per-user ownership checks on every endpoint.
*   **💾 Persistent Meeting History Hub**: Retains meeting metadata, chat threads, transcripts, and action logs across browser restarts, allowing users to rename, reload, or purge sessions.

---

## Repository Structure

```directory
synapse/
├── backend/                  # FastAPI Application Root
│   ├── database/             # Relational Database Configuration
│   │   ├── __init__.py
│   │   ├── connection.py     # SQLAlchemy Connection Pool & Session Generator
│   │   ├── crud.py           # Database CRUD Repository Layer
│   │   └── models.py         # SQLAlchemy ORM Data Models
│   ├── models/               # Pydantic Schemas
│   │   └── schemas.py        # Request/Response Data Transfer Objects (DTOs)
│   ├── prompts/              # Centralized Prompts
│   │   └── defaults.py       # Playbooks, Copilot, & NLP System Prompts
│   ├── migrations/           # Alembic Migration Environment
│   │   └── versions/         # 0001_baseline, 0002_auth
│   ├── routers/              # API Endpoints
│   │   ├── auth.py           # Registration, Login, Logout, Refresh
│   │   ├── chat.py           # Chat Copilot Streaming Router
│   │   ├── history.py        # Session History Hub Router
│   │   ├── intelligence.py   # Sentiment & Action Item Extraction Router
│   │   ├── meeting.py        # Session Management Router
│   │   ├── suggestions.py    # Playbook Live Suggestion Router
│   │   └── transcribe.py     # Groq Whisper Transcription Router
│   ├── security/             # Authentication Primitives
│   │   ├── cookies.py        # Cookie Names & Policy
│   │   ├── passwords.py      # Argon2id Hashing
│   │   ├── ratelimit.py      # Sliding-Window Rate Limiter
│   │   └── tokens.py         # Access / Refresh JWT Issuing
│   ├── services/             # Third-Party Clients
│   │   └── groq_client.py    # Async HTTPX Client Wrapper for Groq API
│   ├── tests/                # Pytest Suite (120 tests)
│   ├── alembic.ini           # Migration Configuration
│   ├── cli.py                # Operational CLI (migrate, users, legacy data)
│   ├── config.py             # Environment-Driven Settings
│   ├── dependencies.py       # Auth, CSRF, Rate Limit & Ownership Guards
│   ├── main.py               # Application Entry Point & Lifespan Context
│   └── requirements.txt      # Python Dependencies
├── client/                   # React Single-Page Application Root
│   ├── public/               # Static Web Assets
│   ├── src/                  # React Source Code
│   │   ├── components/       # Reusable UI Elements
│   │   │   ├── AuthProvider.jsx        # Cookie Session State
│   │   │   ├── AuthScreen.jsx          # Login & Registration
│   │   │   ├── HistorySidebar.jsx      # Historical Meetings Hub
│   │   │   ├── LiveSuggestionsPanel.jsx # Live Suggestion Stream Container
│   │   │   ├── Navbar.jsx              # Global Brand, Theme & Settings Modal
│   │   │   ├── SuggestionCard.jsx      # Individual Suggestion Details Card
│   │   │   ├── TranscriptPanel.jsx     # Recording Controls & Canvas Visualizer
│   │   │   └── WorkspacePanel.jsx      # AI Chat & Board Tabs Container
│   │   ├── api.js            # Fetch Wrappers, Auth & Stream Decoders
│   │   ├── App.jsx           # Route Gate & Master Coordinator
│   │   ├── authContext.js    # Auth Context & useAuth Hook
│   │   ├── index.html        # HTML Entrypoint
│   │   ├── sessionSettings.js# Local Browser Storage Engine
│   │   └── styles.css        # Premium Dark-Theme System Configuration
│   ├── package.json          # Node.js Project Configuration
│   └── vite.config.js        # Vite Bundler Configuration
├── render.yaml               # Render Blueprint (backend + PostgreSQL)
├── synapse.db                # SQLite Local Database (git-ignored)
└── SYSTEM_DESIGN.md          # Architectural Specifications & Trade-offs
```

---

## Detailed API Specification

Every route below `/api` is authenticated except `GET /`, `GET /api/health`,
`GET /healthz` and the `/api/auth/register` + `/api/auth/login` endpoints.

Each request carries two independent credentials:

| Credential | Transport | Stored where |
|---|---|---|
| Session | `synapse_access` / `synapse_refresh` HTTP-only cookies, sent automatically | Server-side `auth_sessions` row; only a SHA-256 digest of the refresh token |
| CSRF token | `X-CSRF-Token` header, mirroring the readable `synapse_csrf` cookie | Nowhere — regenerated per session |
| Groq API key | `X-Groq-API-Key` header | Browser `sessionStorage` only, **never** server-side |

State-changing requests (`POST`, `PUT`, `PATCH`, `DELETE`) require the CSRF
header. Requests referencing a `session_id` — in the path *or* the body — are
rejected with `403` unless the authenticated user owns that meeting.

| Status | Meaning |
|---|---|
| `401` | No session, or it expired / was revoked |
| `403` | Authenticated, but the CSRF token is missing or the resource belongs to another user |
| `404` | The resource does not exist |
| `409` | Email already registered |
| `413` | Request body or audio upload over the limit |
| `422` | Validation failed (submitted values are never echoed back) |
| `429` | Rate limited, or the account is temporarily locked |

### 1. Authentication

#### `POST /api/auth/register`
Creates an account and signs it in immediately.
*   **Request Payload**:
    ```json
    {
      "email": "you@company.com",
      "password": "at-least-10-chars-with-a-number-1",
      "full_name": "Ada Lovelace"
    }
    ```
*   **Success Response (`201 Created`)** — sets `synapse_access`, `synapse_refresh` and `synapse_csrf`:
    ```json
    {
      "user": {
        "id": "a1b2c3d4-...",
        "email": "you@company.com",
        "full_name": "Ada Lovelace",
        "created_at": "2026-06-14T22:15:00Z"
      },
      "expires_in": 1800
    }
    ```

#### `POST /api/auth/login`
Verifies credentials and opens a new session. Returns the same body as register.
Responds `401` with the identical message for both an unknown email and a wrong
password, so accounts cannot be enumerated.

#### `POST /api/auth/refresh`
Rotates both tokens. Replaying a superseded refresh token is treated as a leak:
every session for that account is revoked.

#### `POST /api/auth/logout`
Revokes the server-side session and clears all three cookies. A still-valid
access token stops working immediately.

#### `GET /api/auth/me`
Returns the signed-in user, or `401`. This is what restores the session after a
browser refresh.

#### `POST /api/auth/password`
Changes the password, signs every other device out, and re-issues cookies for
the calling browser.

### 2. Meeting Management

#### `POST /api/meeting/start`
Initializes a new meeting session, creates a database record, and locks in settings.
*   **Request Payload**:
    ```json
    {
      "playbook": "general",
      "meeting_memory": "Prior notes: discussing UI updates.",
      "title": "Marketing Synch-Up"
    }
    ```
*   **Success Response (`200 OK`)**:
    ```json
    {
      "session_id": "4a1b2c3d-5e6f-7a8b-9c0d-1e2f3a4b5c6d",
      "started_at": "2026-06-14T22:15:00Z",
      "status": "active"
    }
    ```

#### `POST /api/meeting/end`
Closes the active session, timestamping the end time.
*   **Request Payload**:
    ```json
    {
      "session_id": "4a1b2c3d-5e6f-7a8b-9c0d-1e2f3a4b5c6d"
    }
    ```
*   **Success Response (`200 OK`)**:
    ```json
    {
      "session_id": "4a1b2c3d-5e6f-7a8b-9c0d-1e2f3a4b5c6d",
      "ended_at": "2026-06-14T22:45:00Z",
      "status": "ended"
    }
    ```

#### `POST /api/history/{session_id}/transcript`
Persists one captured transcript segment against its meeting. The client calls
this for each speech segment as it is transcribed, which is what gives a saved
meeting a transcript in history.
*   **Request Payload**:
    ```json
    {
      "text": "The login button is misaligned in Chrome.",
      "time": "10:01:00",
      "isoTime": "2026-06-14T10:01:00Z",
      "kind": "speech"
    }
    ```
*   **Success Response (`201 Created`)**:
    ```json
    { "id": "7f3c1a9e-..." }
    ```

### 3. Audio & AI Services

#### `POST /api/transcribe`
Uploads a raw audio blob chunk to convert to text.
*   **Headers**: `Content-Type: multipart/form-data`
*   **Request Body**: Multipart form containing `audio_file` (WebM/Opus binary).
*   **Success Response (`200 OK`)**:
    ```json
    {
      "text": "Hello team, let's start the design review today."
    }
    ```

#### `POST /api/suggestions`
Generates three scenario-based suggestions based on the playbook and current transcript.
*   **Request Payload**:
    ```json
    {
      "transcript_slice": "We need to fix the login button styling. It's misaligned in Chrome.",
      "playbook": "design",
      "previous_suggestions": ["Fix visual constraints", "Audit button alignment"],
      "session_id": "4a1b2c3d-5e6f-7a8b-9c0d-1e2f3a4b5c6d",
      "model": "llama-3.3-70b-versatile"
    }
    ```
*   **Success Response (`200 OK`)**:
    ```json
    {
      "suggestions": [
        {
          "type": "TALKING_POINT",
          "title": "Chrome Render Engine Flexbox Bug",
          "preview": "Discuss potential CSS flexbox incompatibilities in chromium browsers."
        },
        {
          "type": "QUESTION_TO_ASK",
          "title": "Safari Test Case Scope",
          "preview": "Should we also test visual alignment on WebKit/Safari engine?"
        },
        {
          "type": "ANSWER",
          "title": "Apply CSS Lint Override",
          "preview": "Recommend adding cross-browser vendors to the post-css build settings."
        }
      ]
    }
    ```

#### `POST /api/chat`
Streams a conversational response via Server-Sent Events (SSE) based on chat history.
*   **Request Payload**:
    ```json
    {
      "message": "What styling issues were discussed?",
      "chat_history": [{"role": "user", "content": "Hello"}, {"role": "assistant", "content": "Hi there!"}],
      "full_transcript": "We need to fix the login button styling. It's misaligned in Chrome.",
      "session_id": "4a1b2c3d-5e6f-7a8b-9c0d-1e2f3a4b5c6d",
      "model": "llama-3.1-8b-instant"
    }
    ```
*   **Success Response (`200 OK`, `text/event-stream`)**:
    ```text
    data: {"choices": [{"delta": {"content": "The"}}]}
    data: {"choices": [{"delta": {"content": " login"}}]}
    data: {"choices": [{"delta": {"content": " button"}}]}
    data: [DONE]
    ```

---

## Architecture

```
Browser (React 19 + Vite)
  │  HTTP-only session cookies  ──────────────┐
  │  X-CSRF-Token header                      │
  │  X-Groq-API-Key header (sessionStorage)   │
  ▼                                           ▼
FastAPI backend ───────────────────► Groq LPU cloud
  │   auth → CSRF → rate limit → ownership      (Whisper + Llama 3.3 70B)
  ▼
SQLAlchemy ORM
  ├── SQLite      (local development)
  └── PostgreSQL  (production, via DATABASE_URL)
```

The backend never holds a Groq credential. Each request carries the user's own
key in a header, it is forwarded to Groq, and it is discarded when the request
ends. It is never written to the database, a log line, a session, or an API
response — upstream error bodies are scrubbed of it before they are logged or
returned.

### Authentication design

* **Hashing** — Argon2id (`argon2-cffi`) at 19 MiB / 2 iterations / parallelism 1.
  Hashes are upgraded transparently on login when the parameters change.
* **Sessions** — a 30-minute access JWT and a 14-day refresh JWT, both in
  `HttpOnly; Secure; SameSite` cookies. Each access token names a row in
  `auth_sessions`, which is checked on every request, so logout, a password
  change, or refresh-token reuse revokes live access tokens *immediately*
  rather than at expiry.
* **Refresh rotation** — every refresh issues a new token pair and stores only
  a SHA-256 digest of the refresh token. Presenting a superseded token revokes
  the whole family.
* **CSRF** — double-submit: a readable `synapse_csrf` cookie echoed in
  `X-CSRF-Token`, compared with `secrets.compare_digest` on every unsafe method.
* **Brute force** — a per-process sliding-window limiter on login and
  registration, *plus* a database-backed account lock after repeated failures
  so protection survives restarts and extra instances.
* **Authorization** — `require_owned_session()` guards every endpoint that
  accepts a `session_id`, from path parameters and request bodies alike.

### Persistence notes

* Transcript segments are written through
  `POST /api/history/{session_id}/transcript` as they are captured, so a
  meeting's transcript survives the browser session.
* `POST /api/intelligence` returns the database `id` of every action item it
  persists, so completing or deleting one from the live workspace is saved
  rather than applied only in memory. Items extracted while no meeting is
  active have `id: null` and stay client-side, which is correct — there is no
  row to update.

### Database

Six meeting tables (`meeting_sessions`, `transcript_entries`,
`suggestion_items`, `chat_messages`, `action_items`, `decision_items`) plus two
added for authentication (`users`, `auth_sessions`). The only change to the
original six is a nullable `meeting_sessions.user_id` foreign key.

Meetings recorded before authentication existed keep `user_id = NULL`. They are
preserved on disk but served to nobody until claimed:

```bash
python -m backend.cli claim-legacy-sessions --email you@company.com --dry-run
python -m backend.cli claim-legacy-sessions --email you@company.com
```

---

## Environment Variables

`backend/.env.example` and `client/.env.example` are templates. Never commit a
filled-in `.env`.

### Backend

| Variable | Required | Default | Purpose |
|---|---|---|---|
| `SECRET_KEY` | **production** | random per boot | Signs session JWTs. Rotating it signs everyone out. |
| `DATABASE_URL` | **production** | `sqlite:///./synapse.db` | `postgres://` and `postgresql://` are normalised to the psycopg driver. |
| `ENVIRONMENT` | no | `development` | `production` enables HSTS, hides docs and requires `SECRET_KEY`. |
| `FRONTEND_URL` | **production** | – | Deployed frontend origin; appended to the CORS allowlist. |
| `ALLOWED_ORIGINS` | **production** | localhost dev origins | Comma-separated exact origins. Never `*`. |
| `COOKIE_SAMESITE` | no | `none` in prod, `lax` otherwise | `none` is required for the Vercel→Render cross-site setup. |
| `COOKIE_SECURE` | no | on in prod | Forced on whenever SameSite is `none`. |
| `COOKIE_DOMAIN` | no | host-only | Set only if you serve both tiers from one parent domain. |
| `ACCESS_TOKEN_MINUTES` | no | `30` | Access token lifetime. |
| `REFRESH_TOKEN_DAYS` | no | `14` | Refresh token lifetime. |
| `RUN_MIGRATIONS_ON_STARTUP` | no | on in prod | Applies Alembic migrations during startup. |
| `AUTO_CREATE_TABLES` | no | on outside prod | `create_all()` convenience for local work. |
| `MAX_UPLOAD_BYTES` | no | `26214400` | Audio upload cap (25 MB). |
| `MAX_JSON_BODY_BYTES` | no | `1048576` | JSON body cap. |
| `LOGIN_RATE_LIMIT` / `LOGIN_RATE_WINDOW_SECONDS` | no | `10` / `900` | Failed-login throttle per IP+account. |
| `REGISTER_RATE_LIMIT` / `REGISTER_RATE_WINDOW_SECONDS` | no | `5` / `3600` | Signup throttle per IP. |
| `API_RATE_LIMIT` / `API_RATE_WINDOW_SECONDS` | no | `240` / `60` | Authenticated request throttle per user. |
| `MAX_FAILED_LOGINS` / `ACCOUNT_LOCK_MINUTES` | no | `8` / `15` | Database-backed account lockout. |
| `ENABLE_DOCS` | no | off in prod | Serves `/docs`, `/redoc`, `/openapi.json`. |
| `TRUSTED_HOSTS` | no | `*` | Comma-separated Host allowlist. |

### Frontend

| Variable | Required | Default | Purpose |
|---|---|---|---|
| `VITE_API_BASE` | production | `/api` | Full backend origin including `/api`. Leave unset locally so the Vite proxy handles it. |

---

## Local Development Guide

### Prerequisites
*   **Node.js**: `v18.0.0` or higher
*   **Python**: `v3.11` or higher (3.13 recommended)

### 1. Backend Service Launch

Run from the **repository root** so the `backend` package resolves and SQLite
lands in one predictable place.

```bash
python3 -m venv backend/.venv
source backend/.venv/bin/activate
pip install --upgrade pip
pip install -r backend/requirements.txt
```

```bash
cp backend/.env.example backend/.env
```

```bash
python -m backend.cli migrate
```

```bash
python -m uvicorn backend.main:app --reload --port 8001
```

Swagger UI is at `http://127.0.0.1:8001/docs`; the health probe is
`http://127.0.0.1:8001/healthz`. Port **8001** matches the Vite dev proxy in
`client/vite.config.js`.

### 2. Frontend Client Launch

```bash
cd client && npm install && npm run dev
```

Open `http://127.0.0.1:5173`. Leave `VITE_API_BASE` unset locally: the Vite dev
server proxies `/api` to the backend, which keeps the app same-origin and lets
session cookies work over plain HTTP.

### 3. First Run

1. Register an account on the sign-in screen.
2. Open **Settings** in the navbar and paste your Groq API key (`gsk_...`).
   It is held in this browser tab's `sessionStorage` and sent per request —
   it is not part of your account and is cleared when you sign out.
3. Start recording.

You can also create an account from the command line:

```bash
python -m backend.cli create-user --email you@company.com
```

---

## Database Migrations

Alembic owns the schema. Two revisions exist: `0001_baseline` (the six original
meeting tables) and `0002_auth` (users, auth sessions, meeting ownership).

Both are written defensively — tables and columns that already exist are left
untouched — so the same `upgrade head` works on a brand-new PostgreSQL database
and on an existing SQLite file created before Alembic was introduced, without
dropping any data.

```bash
python -m backend.cli migrate
```

```bash
cd backend && alembic revision --autogenerate -m "describe the change"
```

Other operational commands:

```bash
python -m backend.cli list-users
```

```bash
python -m backend.cli purge-expired-sessions
```

---

## Testing

```bash
pip install -r backend/requirements-dev.txt
```

```bash
cd backend && python -m pytest
```

The suite covers registration, login, logout, session expiry and revocation,
refresh rotation and reuse detection, CSRF, rate limiting, account lockout,
CORS, security headers, payload limits, SQL-injection attempts, cross-user
isolation for every endpoint that takes a `session_id`, and regression cover
for transcription, the three-attempt suggestion retry ladder, all four
playbooks, intelligence extraction with its empty-schema fallback, and the
streaming copilot.

```bash
cd client && npm run lint && npm run build
```

---

## Production Deployment

**Frontend:** Vercel · **Backend:** Render · **Database:** Render managed PostgreSQL.

### Backend (Render)

`render.yaml` is a blueprint that provisions the web service and the database
together. `SECRET_KEY` is generated by Render and `DATABASE_URL` is wired from
the managed database, so no secret is ever committed.

1. In Render, choose **New → Blueprint** and point it at this repository.
2. Once the service exists, set the two dashboard-only variables:
   * `FRONTEND_URL` — `https://<your-app>.vercel.app`
   * `ALLOWED_ORIGINS` — the same origin, plus any preview domains, comma separated
3. Deploy. Migrations run automatically on startup
   (`RUN_MIGRATIONS_ON_STARTUP=true`).
4. Confirm the two probes:
   * `GET /healthz` — `{"status":"ok","environment":"production"}`. Deliberately
     does **not** touch the database, so a slow or briefly unavailable database
     cannot fail the deploy's health check and trigger a rollback loop. If it
     reports a `configuration_warnings` array, fix those first — the service is
     up but will not work.
   * `GET /readyz` — `{"status":"ok","database":"reachable"}`, or `503` if the
     database cannot be reached.

> **Do not remove the `PYTHON_VERSION` pin.** Render's default for newly created
> services is now 3.14.x, and `pydantic-core` and `psycopg-binary` publish no
> cp314 wheels yet — the build falls back to a source compile and fails. The
> blueprint pins 3.13.5, which is the version the test suite is verified on.

> Render's **free** PostgreSQL plan expires 30 days after creation. Upgrade the
> `databases.plan` entry in `render.yaml` before relying on it.

> The free web plan sleeps when idle, so the first request after a pause takes
> a few seconds. The app already warms the backend up on load.

### Frontend (Vercel)

1. Import the repository and set the **root directory** to `client`.
2. Add the environment variable:
   * `VITE_API_BASE` — `https://<your-service>.onrender.com/api`
3. Deploy. `client/vercel.json` handles SPA routing and sends the static
   security headers.
4. Go back to Render and make sure `FRONTEND_URL` / `ALLOWED_ORIGINS` match the
   final Vercel domain, then redeploy the backend.

### Why the cookie settings matter

The frontend and backend sit on different registrable domains
(`vercel.app` and `onrender.com`), so session cookies are cross-site. That
requires `SameSite=None` **and** `Secure`, which is why both tiers must be
served over HTTPS and why CORS uses an explicit origin allowlist with
`allow_credentials=True` — a wildcard origin is rejected by browsers for
credentialed requests, and is unsafe regardless.

Session cookies are additionally sent with the CHIPS `Partitioned` attribute,
so they keep working in browsers that partition or restrict third-party
cookies. Browsers that do not recognise the attribute ignore it.

**Safari caveat.** Safari blocks third-party cookies outright, and `Partitioned`
does not change that. With the frontend on `vercel.app` and the API on
`onrender.com`, Safari users will not stay signed in. Two ways to fix it, both
making the cookies first-party:

* **Proxy the API through Vercel (no custom domain needed).** Add a rewrite to
  `client/vercel.json` *above* the SPA rule, leave `VITE_API_BASE` unset so the
  app calls same-origin `/api`, and set `COOKIE_SAMESITE=lax` on Render:

  ```json
  "rewrites": [
    { "source": "/api/:path*", "destination": "https://<your-service>.onrender.com/api/:path*" },
    { "source": "/(.*)", "destination": "/index.html" }
  ]
  ```

  Verify the streaming copilot still works after this change — the chat endpoint
  uses Server-Sent Events, and a proxy that buffers responses would break it.

* **Use one parent domain**, e.g. `app.example.com` and `api.example.com`, and
  set `COOKIE_DOMAIN=.example.com` with `COOKIE_SAMESITE=lax`.

Microphone capture also requires a secure context; HTTPS on Vercel satisfies
this, as does `localhost` during development.

---

## Security Summary

| Area | Implementation |
|---|---|
| Password storage | Argon2id, 19 MiB / t=2, transparent rehash on login |
| Session transport | HTTP-only, Secure, SameSite cookies — never `localStorage` |
| Session revocation | Server-side `auth_sessions` row checked per request |
| Refresh tokens | Rotated per use, stored as SHA-256 digests, reuse revokes the family |
| CSRF | Double-submit cookie + header, constant-time comparison |
| CORS | Explicit origin allowlist, credentials enabled, no wildcard |
| Brute force | Sliding-window IP/account limiter + database-backed account lockout |
| API rate limiting | Per-user sliding window on authenticated requests |
| Upload limits | 25 MB audio cap enforced while streaming, plus a Content-Length check |
| Input validation | Pydantic models with explicit field constraints |
| SQL injection | SQLAlchemy parameter binding throughout; no string-built SQL |
| Error handling | Generic 500s, validation errors never echo submitted values |
| Secret exposure | Groq keys scrubbed from logs and upstream error bodies |
| Security headers | CSP, HSTS, nosniff, DENY framing, Referrer-Policy, COOP/CORP |
| Secret management | Everything from the environment; `.env` and `*.db` are git-ignored |

Concurrent startup migrations are serialised with a PostgreSQL advisory
lock, so overlapping deploys or a scale-up cannot race each other into a
half-applied schema.

Known limitation: the in-process rate limiter counts per instance. On the
single-instance Render plan this is exact; if you scale out, move it to Redis.
The database-backed account lockout is unaffected and remains accurate.
