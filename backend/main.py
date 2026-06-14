from pathlib import Path
import sys
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse

if __package__ is None or __package__ == "":
    sys.path.append(str(Path(__file__).resolve().parent.parent))

from backend.routers import chat, meeting, suggestions, transcribe, history, intelligence
from backend.services.groq_client import close_http_client, get_http_client
from backend.database.connection import create_tables


@asynccontextmanager
async def lifespan(_: FastAPI):
    create_tables()
    await get_http_client()
    try:
        yield
    finally:
        await close_http_client()


app = FastAPI(title="Synapse – Live Audio Intelligence", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

for router in [transcribe.router, suggestions.router, chat.router, meeting.router, history.router, intelligence.router]:
    app.include_router(router, prefix="/api")
    app.include_router(router)


@app.get("/", tags=["health"])
async def root():
    return {"status": "ok", "app": "Synapse", "docs": "/docs"}


@app.get("/api/health", tags=["health"])
async def api_health():
    return {"status": "ok"}


@app.get("/api/docs", include_in_schema=False)
async def api_docs_redirect():
    return RedirectResponse(url="/docs", status_code=307)


@app.get("/api/openapi.json", include_in_schema=False)
async def api_openapi_redirect():
    return RedirectResponse(url="/openapi.json", status_code=307)
