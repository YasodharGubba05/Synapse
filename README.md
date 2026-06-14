# Synapse — Real-Time Meeting Intelligence Platform

[![FastAPI](https://img.shields.io/badge/FastAPI-009688?style=for-the-badge&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![React](https://img.shields.io/badge/React-20232A?style=for-the-badge&logo=react&logoColor=61DAFB)](https://react.dev)
[![Groq LPU](https://img.shields.io/badge/Groq_LPU-F55C5C?style=for-the-badge&logo=openai&logoColor=white)](https://groq.com)
[![SQLite](https://img.shields.io/badge/SQLite-07405E?style=for-the-badge&logo=sqlite&logoColor=white)](https://sqlite.org)
[![Python](https://img.shields.io/badge/Python_3.10+-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://python.org)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg?style=for-the-badge)](https://opensource.org/licenses/MIT)

Synapse is an enterprise-grade, real-time meeting copilot and intelligence platform. It ingests live audio streams from your browser, transcribes them in rolling segments, executes periodic natural language processing (NLP) to extract tasks and decisions, visualizes conversational sentiment, and features a context-aware AI assistant.

Built on a decoupled architecture, Synapse combines a **FastAPI asynchronous backend**, **Groq's LPU (Language Processing Unit) inference cloud**, a **React 19 single-page client**, and a **persistent local SQLite database** via a robust SQLAlchemy ORM layer.

---

## Key Capabilities

*   **🎙️ Asynchronous Audio Chunking Pipeline**: Ingests rolling 30-second audio segments from the client browser using the Web MediaStream and MediaRecorder APIs. This keeps latency minimal and protects against network-related data loss.
*   **📊 Canvas-Based Audio Visualizer**: Renders real-time mic frequency data using the Web Audio API (`AnalyserNode` with Fast Fourier Transforms) directly to an HTML5 Canvas, eliminating layout reflows and reducing CPU overhead.
*   **🎯 Scenario-Specific Playbooks**: Features hot-swappable suggestion models tailored for common business meetings (General Meeting, Daily Standup, Product Design, Sales Discovery).
*   **📋 Structured Workspace Boards**: Automatically extracts action items (categorized by assignee and High/Medium/Low priority) and log decisions. Tracks and updates action statuses (pending/completed) directly in the database.
*   **📈 Real-Time Sentiment & Keywords**: Visualizes ongoing meeting sentiment (Positive, Constructive, Neutral, Conflicted) and maps core keywords.
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
│   ├── routers/              # API Endpoints
│   │   ├── chat.py           # Chat Copilot Streaming Router
│   │   ├── history.py        # Session History Hub Router
│   │   ├── intelligence.py   # Sentiment & Action Item Extraction Router
│   │   ├── meeting.py        # Session Management Router
│   │   ├── suggestions.py    # Playbook Live Suggestion Router
│   │   └── transcribe.py     # Groq Whisper Transcription Router
│   ├── services/             # Third-Party Clients
│   │   └── groq_client.py    # Async HTTPX Client Wrapper for Groq API
│   ├── main.py               # Application Entry Point & Lifespan Context
│   └── requirements.txt      # Python Dependencies
├── client/                   # React Single-Page Application Root
│   ├── public/               # Static Web Assets
│   ├── src/                  # React Source Code
│   │   ├── components/       # Reusable UI Elements
│   │   │   ├── HistorySidebar.jsx      # Historical Meetings Hub
│   │   │   ├── LiveSuggestionsPanel.jsx # Live Suggestion Stream Container
│   │   │   ├── Navbar.jsx              # Global Brand, Theme & Settings Modal
│   │   │   ├── SuggestionCard.jsx      # Individual Suggestion Details Card
│   │   │   ├── TranscriptPanel.jsx     # Recording Controls & Canvas Visualizer
│   │   │   └── WorkspacePanel.jsx      # AI Chat & Board Tabs Container
│   │   ├── api.js            # Fetch Wrappers & Stream Decoders
│   │   ├── App.jsx           # Master Application Coordinator
│   │   ├── index.html        # HTML Entrypoint
│   │   ├── sessionSettings.js# Local Browser Storage Engine
│   │   └── styles.css        # Premium Dark-Theme System Configuration
│   ├── package.json          # Node.js Project Configuration
│   └── vite.config.js        # Vite Bundler Configuration
├── synapse.db                # SQLite Local Database (Auto-generated)
└── SYSTEM_DESIGN.md          # Architectural Specifications & Trade-offs
```

---

## Detailed API Specification

All endpoints require the Groq API key in the `X-Groq-API-Key` request header.

### 1. Meeting Management

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

### 2. Audio & AI Services

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
```bash
# Clone the repository and enter backend directory
cd backend

# Setup virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install requirements
pip install --upgrade pip
pip install -r requirements.txt

# Start FastAPI hot-reload server
python3 -m uvicorn main:app --reload --port 8000
```
Verify backend operation by accessing the Swagger UI documentation at `http://127.0.0.1:8000/docs`.

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

### 3. Application Authentication
In the browser UI, click the **Settings** cog in the navbar. Input your **Groq API Key** (`gsk_...`). This key is retained in the browser tab's `sessionStorage` and sent securely with each API request header.

---

## Containerized Local Deployment (Docker)

To run the entire stack locally in containers without node/python dependencies, use the following `docker-compose.yml` config:

```yaml
version: '3.8'

services:
  backend:
    image: python:3.11-slim
    volumes:
      - ./backend:/app
      - ./synapse.db:/app/synapse.db
    working_dir: /app
    ports:
      - "8000:8000"
    command: sh -c "pip install -r requirements.txt && uvicorn main:app --host 0.0.0.0 --port 8000"
    environment:
      - PYTHONUNBUFFERED=1

  client:
    image: node:18-alpine
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

## Production Security & Deployment Heuristics

*   **HTTPS and SSL/TLS Enforcements**: When deploying, always serve the client and backend under HTTPS (TLS 1.3). This prevents network eavesdropping of the `X-Groq-API-Key` headers.
*   **CORS Configurations**: Update the `CORSMiddleware` setup in `backend/main.py` to lock down allowed origins (`allow_origins=["https://your-domain.com"]`) instead of allowing all origins (`*`).
*   **Database Scaling**: To transition from local SQLite to PostgreSQL, update the `DATABASE_URL` environment variable in the backend to a connection string such as `postgresql://user:password@host:port/database` and run migrations.
*   **Vercel & Render Configurations**: 
    *   Deploy the React client to Vercel (configurations are defined in `client/vercel.json`).
    *   Deploy the Python FastAPI backend to Render using a persistent disk mount for SQLite, or configure an external database.
