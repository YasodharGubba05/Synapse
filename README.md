# Synapse — Real-Time Meeting Intelligence Platform

[![FastAPI](https://img.shields.io/badge/FastAPI-009688?style=for-the-badge&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![React](https://img.shields.io/badge/React-20232A?style=for-the-badge&logo=react&logoColor=61DAFB)](https://react.dev)
[![Groq LPU](https://img.shields.io/badge/Groq_LPU-F55C5C?style=for-the-badge&logo=openai&logoColor=white)](https://groq.com)
[![SQLite](https://img.shields.io/badge/SQLite-07405E?style=for-the-badge&logo=sqlite&logoColor=white)](https://sqlite.org)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-4169E1?style=for-the-badge&logo=postgresql&logoColor=white)](https://postgresql.org)
[![Python](https://img.shields.io/badge/Python_3.10+-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://python.org)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg?style=for-the-badge)](https://opensource.org/licenses/MIT)

### 🔗 Live Application

| | |
|---|---|
| **Live App** | **https://synapse-two-kappa.vercel.app** |
| **API** | https://synapse-backend-dhuv.onrender.com |
| **API Health** | https://synapse-backend-dhuv.onrender.com/healthz |

> Create an account, then add your own Groq API key under **Settings** to enable
> transcription and AI features. The key stays in your browser tab and is never
> stored on the server.

---

Synapse is an enterprise-grade, real-time meeting copilot and intelligence platform. It ingests live audio streams from your browser, transcribes them in rolling segments, executes periodic natural language processing (NLP) to extract tasks and decisions, visualizes conversational sentiment, and features a context-aware AI assistant.

Built on a decoupled architecture, Synapse combines a **FastAPI asynchronous backend**, **Groq's LPU (Language Processing Unit) inference cloud**, a **React 19 single-page client**, and a **SQLAlchemy ORM layer** running on SQLite locally and managed PostgreSQL in production. Every workspace is protected by cookie-based authentication, and each account sees only its own meetings, transcripts, and action logs.

---

## Key Capabilities

*   **🎙️ Asynchronous Audio Chunking Pipeline**: Ingests rolling 30-second audio segments from the client browser using the Web MediaStream and MediaRecorder APIs. This keeps latency minimal and protects against network-related data loss.
*   **📊 Canvas-Based Audio Visualizer**: Renders real-time mic frequency data using the Web Audio API (`AnalyserNode` with Fast Fourier Transforms) directly to an HTML5 Canvas, eliminating layout reflows and reducing CPU overhead.
*   **🎯 Scenario-Specific Playbooks**: Features hot-swappable suggestion models tailored for common business meetings (General Meeting, Daily Standup, Product Design, Sales Discovery).
*   **📋 Structured Workspace Boards**: Automatically extracts action items (categorized by assignee and High/Medium/Low priority) and log decisions. Tracks and updates action statuses (pending/completed) directly in the database.
*   **📈 Real-Time Sentiment & Keywords**: Visualizes ongoing meeting sentiment (Positive, Constructive, Neutral, Conflicted) and maps core keywords.
*   **🔐 Authenticated, Account-Isolated Workspaces**: Argon2id password hashing, HTTP-only cookie sessions with rotating refresh tokens, CSRF protection, and per-user ownership checks enforced on every endpoint.
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
│   │   └── versions/         # 0001_baseline · 0002_auth
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
│   │   └── tokens.py         # Access / Refresh Token Issuing
│   ├── services/             # Third-Party Clients
│   │   └── groq_client.py    # Async HTTPX Client Wrapper for Groq API
│   ├── tests/                # Pytest Suite (132 tests)
│   ├── cli.py                # Operational CLI (migrate, users, legacy data)
│   ├── config.py             # Environment-Driven Settings
│   ├── db_migrate.py         # Lock-Guarded Migration Runner
│   ├── dependencies.py       # Auth, CSRF, Rate Limit & Ownership Guards
│   ├── main.py               # Application Entry Point & Lifespan Context
│   └── requirements.txt      # Python Dependencies
├── client/                   # React Single-Page Application Root
│   ├── public/               # Static Web Assets
│   ├── src/                  # React Source Code
│   │   ├── components/       # Reusable UI Elements
│   │   │   ├── AuthProvider.jsx        # Cookie Session State
│   │   │   ├── AuthScreen.jsx          # Login & Registration Interface
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

## System Design

A full treatment of the architecture, trade-offs, and scaling guidelines lives in
[SYSTEM_DESIGN.md](SYSTEM_DESIGN.md). The essentials:

```
                  ┌─────────────────────────────────────────┐
   Microphone ──▶ │  React 19 SPA  (Vercel)                 │
                  │  MediaRecorder · Canvas Visualizer      │
                  │  Groq key in sessionStorage             │
                  └──────────────┬──────────────────────────┘
                                 │  same-origin /api
                                 │  (Vercel rewrite → Render)
                                 ▼
                  ┌─────────────────────────────────────────┐
                  │  FastAPI  (Render)                      │
                  │  auth → CSRF → rate limit → ownership   │
                  └───────┬──────────────────────┬──────────┘
                          │                      │
                          ▼                      ▼
             ┌────────────────────┐   ┌────────────────────────┐
             │ SQLAlchemy ORM     │   │  Groq LPU Cloud        │
             │ SQLite  (local)    │   │  Whisper-Large-v3      │
             │ PostgreSQL (prod)  │   │  Llama 3.3 70B         │
             └────────────────────┘   └────────────────────────┘
```

### Request Pipeline

Every protected request passes four gates before it reaches business logic:
**authentication** (resolve the session from the access cookie and confirm its
server-side record is still active) → **CSRF** (double-submit comparison on
every unsafe method) → **rate limiting** (per-user sliding window) →
**ownership** (the authenticated user must own the `session_id`, whether it
arrives in the path or the request body).

### Authentication Architecture

*   **Hashing**: Argon2id (19 MiB, t=2, p=1), the OWASP default. Hashes are
    upgraded transparently on login if the parameters change.
*   **Sessions**: a 30-minute access token and a 14-day refresh token, both in
    `HttpOnly; Secure; SameSite` cookies — never `localStorage`. Each access
    token names a row in `auth_sessions` that is checked on every request, so
    logout, a password change, or token reuse revokes live tokens *immediately*
    rather than at expiry.
*   **Rotation**: every refresh issues a new pair and stores only a SHA-256
    digest of the refresh token. Replaying a superseded token is treated as a
    leak and revokes the entire session family.
*   **Brute force**: a sliding-window limiter on login and registration, backed
    by a database-level account lockout that survives restarts and extra
    instances.
*   **Same-origin by design**: the deployed frontend proxies `/api` to the
    backend, so session cookies are first-party. Cross-site cookies cannot be
    read by page scripts (which breaks double-submit CSRF) and are blocked
    outright by Safari.

### Data Model

Eight tables: the six original meeting tables — `meeting_sessions`,
`transcript_entries`, `suggestion_items`, `chat_messages`, `action_items`,
`decision_items` — plus `users` and `auth_sessions`. The only change to the
original six is a nullable `meeting_sessions.user_id` foreign key. Meetings
recorded before authentication existed keep `user_id = NULL`; they are
preserved and can be claimed with
`python -m backend.cli claim-legacy-sessions --email <address>`.

### Groq Credential Isolation

The backend never holds a Groq credential. Each request carries the user's own
key in the `X-Groq-API-Key` header; it is forwarded to Groq and discarded when
the request ends. It is never written to the database, a log line, a session,
or an API response, and upstream error bodies are scrubbed of it before being
logged or returned. **Account authentication and Groq credentials are entirely
separate systems.**

---

## Detailed API Specification

All application endpoints require an authenticated session (HTTP-only cookies,
sent automatically by the browser) plus the `X-CSRF-Token` header on any
request that changes state. AI and audio endpoints additionally require the
Groq API key in the `X-Groq-API-Key` request header. Only `/`, `/api/health`,
`/healthz`, `/api/auth/register`, and `/api/auth/login` are public.

| Status | Meaning |
|---|---|
| `401` | No session, or it expired or was revoked |
| `403` | CSRF token missing/invalid, or the resource belongs to another user |
| `404` | Resource does not exist |
| `409` | Email already registered |
| `413` | Body or audio upload over the limit |
| `422` | Validation failed |
| `429` | Rate limited, or the account is temporarily locked |

### 1. Authentication

#### `POST /api/auth/register`
Creates an account and signs it in, returning `synapse_access`,
`synapse_refresh`, and `synapse_csrf` cookies.
*   **Request Payload**:
    ```json
    {
      "email": "you@company.com",
      "password": "at-least-10-chars-with-a-number-1",
      "full_name": "Ada Lovelace"
    }
    ```
*   **Success Response (`201 Created`)**:
    ```json
    {
      "user": {
        "id": "a1b2c3d4-5e6f-7a8b-9c0d-1e2f3a4b5c6d",
        "email": "you@company.com",
        "full_name": "Ada Lovelace",
        "created_at": "2026-06-14T22:15:00Z"
      },
      "expires_in": 1800
    }
    ```

#### `POST /api/auth/login`
Verifies credentials and opens a session; returns the same body as register.
An unknown email and a wrong password produce the identical `401` message, so
accounts cannot be enumerated.

#### `POST /api/auth/refresh`
Rotates both tokens. Replaying a superseded refresh token revokes every session
for that account.

#### `POST /api/auth/logout`
Revokes the server-side session and clears all three cookies.

#### `GET /api/auth/me`
Returns the signed-in user, or `401`. This is what restores the session after a
browser refresh.

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
meeting a transcript in the History Hub.
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
    { "id": "7f3c1a9e-2b4d-4c8a-9e1f-0a5b6c7d8e9f" }
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

## Local Development Guide

### Prerequisites
*   **Node.js**: `v18.0.0` or higher
*   **Python**: `v3.11` or higher (3.13 recommended)

### 1. Backend Service Launch

Run these from the **repository root** so the `backend` package resolves and
the SQLite file lands in one predictable place.

```bash
# Setup virtual environment
python3 -m venv backend/.venv
source backend/.venv/bin/activate

# Install requirements
pip install --upgrade pip
pip install -r backend/requirements.txt

# Create a local .env (SQLite default needs no edits to get started)
cp backend/.env.example backend/.env

# Apply database migrations
python -m backend.cli migrate

# Start FastAPI hot-reload server
python -m uvicorn backend.main:app --reload --port 8001
```
Verify backend operation at `http://127.0.0.1:8001/docs` (Swagger UI) and
`http://127.0.0.1:8001/healthz` (health probe). Port **8001** matches the Vite
dev proxy in `client/vite.config.js`.

### 2. Frontend Client Launch
```bash
# Navigate to the client directory
cd client

# Install NPM modules
npm install

# Run the Vite web server
npm run dev
```
Open your browser and navigate to `http://127.0.0.1:5173`. Leave `VITE_API_BASE`
unset locally: the Vite dev server proxies `/api` to the backend, which keeps
the app same-origin so session cookies work over plain HTTP.

### 3. Create an Account

Register on the sign-in screen, or from the command line:

```bash
python -m backend.cli create-user --email you@company.com
```

### 4. Add Your Groq API Key
In the browser UI, click the **Settings** cog in the navbar. Input your **Groq API Key** (`gsk_...`). This key is retained in the browser tab's `sessionStorage` and sent securely with each API request header. It is not part of your account and is cleared when you sign out.

### 5. Database Migrations

Alembic owns the schema. Both revisions are written defensively — anything that
already exists is left untouched — so the same command works on a brand-new
PostgreSQL database and on a pre-existing SQLite file without dropping data.

```bash
python -m backend.cli migrate                                   # upgrade to head
python -m backend.cli list-users                                # list accounts
python -m backend.cli claim-legacy-sessions --email you@co.com  # adopt pre-auth meetings
cd backend && alembic revision --autogenerate -m "describe it"  # new revision
```

### 6. Running the Test Suite

```bash
pip install -r backend/requirements-dev.txt
cd backend && python -m pytest          # 132 tests
cd client && npm run lint && npm run build
```

---

## Containerized Local Deployment (Docker)

To run the entire stack locally in containers without node/python dependencies, use the following `docker-compose.yml` config:

```yaml
version: '3.8'

services:
  backend:
    image: python:3.13-slim
    volumes:
      - .:/app
    working_dir: /app
    ports:
      - "8001:8001"
    command: >
      sh -c "pip install -r backend/requirements.txt &&
             python -m backend.cli migrate &&
             uvicorn backend.main:app --host 0.0.0.0 --port 8001"
    environment:
      - PYTHONUNBUFFERED=1
      - SECRET_KEY=local-development-only-change-me
      - ALLOWED_ORIGINS=http://localhost:5173

  client:
    image: node:20-alpine
    volumes:
      - ./client:/app
    working_dir: /app
    ports:
      - "5173:5173"
    command: sh -c "npm install && npm run dev -- --host"
    depends_on:
      - backend
```
Launch the system with:
```bash
docker-compose up --build
```

---

## Environment Variables

### Backend

| Variable | Required | Default | Purpose |
|---|---|---|---|
| `SECRET_KEY` | **production** | random per boot | Signs session tokens. Rotating it signs everyone out. |
| `DATABASE_URL` | **production** | `sqlite:///./synapse.db` | `postgres://` and `postgresql://` are normalised to the psycopg driver. |
| `ENVIRONMENT` | no | `development` | `production` enables HSTS, hides docs, requires `SECRET_KEY`. |
| `FRONTEND_URL` | **production** | – | Deployed frontend origin; appended to the CORS allowlist. |
| `ALLOWED_ORIGINS` | **production** | localhost dev origins | Comma-separated exact origins. Never `*`. |
| `COOKIE_SAMESITE` / `COOKIE_SECURE` | no | `lax` / on in prod | `lax` when the API is same-origin (the deployed setup). |
| `ACCESS_TOKEN_MINUTES` / `REFRESH_TOKEN_DAYS` | no | `30` / `14` | Session lifetimes. |
| `RUN_MIGRATIONS_ON_STARTUP` | no | on in prod | Applies Alembic migrations during startup. |
| `MAX_UPLOAD_BYTES` / `MAX_JSON_BODY_BYTES` | no | `26214400` / `1048576` | Audio and JSON body caps. |
| `LOGIN_RATE_LIMIT` / `REGISTER_RATE_LIMIT` / `API_RATE_LIMIT` | no | `10` / `5` / `240` | Throttles per window. |
| `MAX_FAILED_LOGINS` / `ACCOUNT_LOCK_MINUTES` | no | `8` / `15` | Database-backed account lockout. |
| `ENABLE_DOCS` | no | off in prod | Serves `/docs` and `/openapi.json`. |
| `PYTHON_VERSION` | **Render** | – | Pinned to `3.13.5`. See the warning below. |

See `backend/.env.example` and `client/.env.example` for complete templates.

---

## Production Deployment

**Frontend:** Vercel · **Backend:** Render · **Database:** Render managed PostgreSQL.

The live deployment is at
**https://synapse-two-kappa.vercel.app**, backed by
`https://synapse-backend-dhuv.onrender.com`.

### Backend (Render)

`render.yaml` is a blueprint that provisions the web service and the database
together. `SECRET_KEY` is generated by Render and `DATABASE_URL` is wired from
the managed database, so no secret is ever committed.

1. In Render, choose **New → Blueprint** and point it at this repository.
2. Set the two dashboard-only variables once the Vercel domain exists:
   `FRONTEND_URL` and `ALLOWED_ORIGINS`.
3. Deploy. Migrations run automatically on startup, serialised across instances
   by a PostgreSQL advisory lock.
4. Confirm the probes:
   * `GET /healthz` → `{"status":"ok","environment":"production"}`. Deliberately
     does **not** touch the database, so a slow database cannot fail the deploy's
     health check and trigger a rollback loop. If it returns a
     `configuration_warnings` array, fix those first — the service is up but
     will not work.
   * `GET /readyz` → `{"status":"ok","database":"reachable"}`, or `503`.

> ⚠️ **Do not remove the `PYTHON_VERSION` pin.** Render's default for newly
> created services is now 3.14.x, and `pydantic-core` and `psycopg-binary`
> publish no cp314 wheels — the build falls back to a source compile and fails.
> The blueprint pins `3.13.5`, the version the test suite is verified on.

> Render's **free** PostgreSQL plan expires 30 days after creation, and the free
> web plan sleeps when idle, so the first request after a pause takes a few
> seconds.

### Frontend (Vercel)

1. Import the repository and set the **root directory** to `client`.
2. Deploy. `client/vercel.json` handles SPA routing, the static security
   headers, and the `/api` proxy.

### Why the API is proxied, not called cross-origin

`client/vercel.json` rewrites `/api/*` to the Render backend:

```json
{ "source": "/api/:path*", "destination": "https://<your-backend>.onrender.com/api/:path*" }
```

This is **load-bearing, not an optimisation.** Calling the backend directly
across origins makes the session cookies third-party, and page scripts cannot
read another domain's cookie — so the double-submit CSRF token is always empty
and every state-changing request is rejected with `403`. Safari blocks
third-party cookies outright regardless. Proxying makes the cookies first-party,
so CSRF works, `SameSite` can stay `lax`, and every browser behaves the same.

Leave `VITE_API_BASE` unset in production so the client calls same-origin
`/api`. If you change the backend URL, update the rewrite destination.

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
| Brute force | Sliding-window limiter + database-backed account lockout |
| Upload limits | 25 MB audio cap enforced while streaming, plus Content-Length check |
| Input validation | Pydantic models with explicit field constraints |
| SQL injection | SQLAlchemy parameter binding throughout; no string-built SQL |
| Error handling | Generic 500s; validation errors never echo submitted values |
| Secret exposure | Groq keys scrubbed from logs and upstream error bodies |
| Security headers | CSP, HSTS, nosniff, DENY framing, Referrer-Policy, COOP/CORP |
| Secret management | Everything from the environment; `.env` and `*.db` are git-ignored |

Known limitation: the in-process rate limiter counts per instance. On a
single-instance plan this is exact; if you scale out, move it to Redis. The
database-backed account lockout is unaffected.

---

## License

Released under the [MIT License](https://opensource.org/licenses/MIT).
