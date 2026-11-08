# Synapse — Real-Time Meeting Intelligence Platform

[![FastAPI](https://img.shields.io/badge/FastAPI-009688?style=for-the-badge&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![React](https://img.shields.io/badge/React-20232A?style=for-the-badge&logo=react&logoColor=61DAFB)](https://react.dev)
[![Groq LPU](https://img.shields.io/badge/Groq_LPU-F55C5C?style=for-the-badge&logo=openai&logoColor=white)](https://groq.com)
[![SQLite](https://img.shields.io/badge/SQLite-07405E?style=for-the-badge&logo=sqlite&logoColor=white)](https://sqlite.org)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-4169E1?style=for-the-badge&logo=postgresql&logoColor=white)](https://postgresql.org)
[![Python](https://img.shields.io/badge/Python_3.10+-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://python.org)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg?style=for-the-badge)](https://opensource.org/licenses/MIT)

**🔗 Live App: [synapse-two-kappa.vercel.app](https://synapse-two-kappa.vercel.app)**  ·  API: [synapse-backend-dhuv.onrender.com](https://synapse-backend-dhuv.onrender.com/healthz)

Synapse is an enterprise-grade, real-time meeting copilot and intelligence platform. It ingests live audio streams from your browser, transcribes them in rolling segments, executes periodic natural language processing (NLP) to extract tasks and decisions, visualizes conversational sentiment, and features a context-aware AI assistant.

Built on a decoupled architecture, Synapse combines a **FastAPI asynchronous backend**, **Groq's LPU (Language Processing Unit) inference cloud**, a **React 19 single-page client**, and a **SQLAlchemy ORM layer** running on SQLite locally and managed PostgreSQL in production. Workspaces are protected by cookie-based authentication, so each account sees only its own meetings.

---

## Key Capabilities

*   **🎙️ Asynchronous Audio Chunking Pipeline**: Ingests rolling 30-second audio segments from the client browser using the Web MediaStream and MediaRecorder APIs. This keeps latency minimal and protects against network-related data loss.
*   **📊 Canvas-Based Audio Visualizer**: Renders real-time mic frequency data using the Web Audio API (`AnalyserNode` with Fast Fourier Transforms) directly to an HTML5 Canvas, eliminating layout reflows and reducing CPU overhead.
*   **🎯 Scenario-Specific Playbooks**: Features hot-swappable suggestion models tailored for common business meetings (General Meeting, Daily Standup, Product Design, Sales Discovery).
*   **📋 Structured Workspace Boards**: Automatically extracts action items (categorized by assignee and High/Medium/Low priority) and log decisions. Tracks and updates action statuses (pending/completed) directly in the database.
*   **📈 Real-Time Sentiment & Keywords**: Visualizes ongoing meeting sentiment (Positive, Constructive, Neutral, Conflicted) and maps core keywords.
*   **🔐 Authenticated Workspaces**: Argon2id password hashing, HTTP-only cookie sessions with rotating refresh tokens, CSRF protection, and per-user ownership checks on every endpoint.
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
│   ├── routers/              # API Endpoints
│   │   ├── auth.py           # Registration, Login, Logout, Refresh
│   │   ├── chat.py           # Chat Copilot Streaming Router
│   │   ├── history.py        # Session History Hub Router
│   │   ├── intelligence.py   # Sentiment & Action Item Extraction Router
│   │   ├── meeting.py        # Session Management Router
│   │   ├── suggestions.py    # Playbook Live Suggestion Router
│   │   └── transcribe.py     # Groq Whisper Transcription Router
│   ├── security/             # Argon2id Hashing, Tokens, Cookies, Rate Limiting
│   ├── services/             # Third-Party Clients
│   │   └── groq_client.py    # Async HTTPX Client Wrapper for Groq API
│   ├── tests/                # Pytest Suite
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
│   │   │   ├── AuthScreen.jsx          # Login & Registration Interface
│   │   │   ├── HistorySidebar.jsx      # Historical Meetings Hub
│   │   │   ├── LiveSuggestionsPanel.jsx # Live Suggestion Stream Container
│   │   │   ├── Navbar.jsx              # Global Brand, Theme & Settings Modal
│   │   │   ├── SuggestionCard.jsx      # Individual Suggestion Details Card
│   │   │   ├── TranscriptPanel.jsx     # Recording Controls & Canvas Visualizer
│   │   │   └── WorkspacePanel.jsx      # AI Chat & Board Tabs Container
│   │   ├── api.js            # Fetch Wrappers & Stream Decoders
│   │   ├── App.jsx           # Route Gate & Master Application Coordinator
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

All application endpoints require an authenticated session (HTTP-only cookies, sent automatically by the browser) and, for any request that changes state, the `X-CSRF-Token` header. AI and audio endpoints additionally require the Groq API key in the `X-Groq-API-Key` request header. Only `/api/health`, `/healthz`, and the register/login routes are public.

Requests referencing a `session_id` are rejected with `403` unless the authenticated user owns that meeting.

### 1. Authentication

| Endpoint | Purpose |
|---|---|
| `POST /api/auth/register` | Create an account and sign in |
| `POST /api/auth/login` | Sign in to an existing account |
| `POST /api/auth/refresh` | Rotate the session tokens |
| `POST /api/auth/logout` | Revoke the session and clear cookies |
| `GET /api/auth/me` | Current user — restores the session after a refresh |

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
*   **Python**: `v3.10.0` or higher

### 1. Backend Service Launch
Run these from the repository root so the `backend` package resolves.

```bash
# Setup virtual environment
python3 -m venv backend/.venv
source backend/.venv/bin/activate

# Install requirements
pip install --upgrade pip
pip install -r backend/requirements.txt

# Create a local .env (the SQLite default needs no edits)
cp backend/.env.example backend/.env

# Apply database migrations
python -m backend.cli migrate

# Start FastAPI hot-reload server
python -m uvicorn backend.main:app --reload --port 8001
```
Verify backend operation by accessing the Swagger UI documentation at `http://127.0.0.1:8001/docs`. Port **8001** matches the Vite dev proxy in `client/vite.config.js`.

### 2. Frontend Client Launch
```bash
# Navigate to the client directory
cd client

# Install NPM modules
npm install

# Run the Vite web server
npm run dev
```
Open your browser and navigate to `http://127.0.0.1:5173`. 

### 3. Create an Account
Register on the sign-in screen, or from the command line with `python -m backend.cli create-user --email you@company.com`. Passwords need at least 10 characters including a letter and a number.

### 4. Application Authentication
In the browser UI, click the **Settings** cog in the navbar. Input your **Groq API Key** (`gsk_...`). This key is retained in the browser tab's `sessionStorage` and sent securely with each API request header. It is never part of your account and is cleared when you sign out.

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
    command: sh -c "pip install -r backend/requirements.txt && python -m backend.cli migrate && uvicorn backend.main:app --host 0.0.0.0 --port 8001"
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

## Production Security & Deployment

Deployed at **[synapse-two-kappa.vercel.app](https://synapse-two-kappa.vercel.app)** — React client on **Vercel**, FastAPI backend and managed **PostgreSQL** on **Render** (`render.yaml` provisions both).

*   **HTTPS and SSL/TLS Enforcements**: Both tiers are served over HTTPS, which prevents network eavesdropping of the `X-Groq-API-Key` header and is also required for microphone capture and `Secure` cookies.
*   **CORS Configurations**: `ALLOWED_ORIGINS` / `FRONTEND_URL` lock the allowlist to the deployed frontend origin — never `*`, which browsers reject for credentialed requests anyway.
*   **Same-Origin API Proxy**: `client/vercel.json` rewrites `/api/*` to the Render backend. This is load-bearing: called cross-origin, the session cookies become third-party, page scripts cannot read them, the CSRF token is always empty, and every state-changing request fails with `403`. Safari blocks third-party cookies outright. Proxying keeps the cookies first-party. Leave `VITE_API_BASE` unset in production.
*   **Database Configuration**: `DATABASE_URL` drives everything — unset for local SQLite, or a managed PostgreSQL connection string in production (`postgres://` and `postgresql://` are both normalised). Migrations run on startup, serialised across instances by an advisory lock.
*   **Python Version Pin**: `PYTHON_VERSION=3.13.5` in `render.yaml` is required. Render's default for new services is now 3.14.x, where `pydantic-core` and `psycopg-binary` have no wheels and the build fails.
*   **Health Probes**: `/healthz` is dependency-free so a database blip cannot fail a deploy and trigger a rollback loop; it also reports `configuration_warnings` for misconfigurations that leave the service up but unusable. `/readyz` checks database reachability.
*   **Credential Handling**: Groq API keys live only in the browser tab's `sessionStorage`, travel per request in a header, and are never written to the database, logs, or API responses — upstream error bodies are scrubbed of them. Passwords are stored only as Argon2id hashes; refresh tokens only as SHA-256 digests.
*   **Required Environment Variables**: `SECRET_KEY`, `DATABASE_URL`, `FRONTEND_URL`, `ALLOWED_ORIGINS`, `PYTHON_VERSION`. See `backend/.env.example` for the full list with defaults.

> Render's free PostgreSQL plan expires 30 days after creation, and the free web plan sleeps when idle, so the first request after a pause takes a few seconds.
