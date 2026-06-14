from typing import Any, AsyncGenerator, Optional

import httpx
from fastapi import HTTPException

GROQ_BASE = "https://api.groq.com/openai/v1"

_client: Optional[httpx.AsyncClient] = None


async def get_http_client() -> httpx.AsyncClient:
    global _client
    if _client is None:
        _client = httpx.AsyncClient(timeout=60.0)
    return _client


async def close_http_client() -> None:
    global _client
    if _client is not None:
        await _client.aclose()
        _client = None


def _build_auth_headers(api_key: str, json_payload: bool = True) -> dict[str, str]:
    headers = {"Authorization": f"Bearer {api_key}"}
    if json_payload:
        headers["Content-Type"] = "application/json"
    return headers


async def groq_post(endpoint: str, api_key: str, payload: dict[str, Any]) -> dict[str, Any]:
    client = await get_http_client()
    response = await client.post(
        f"{GROQ_BASE}{endpoint}",
        headers=_build_auth_headers(api_key),
        json=payload,
    )
    if response.status_code != 200:
        raise HTTPException(status_code=response.status_code, detail=response.text)
    return response.json()


async def groq_post_multipart(
    api_key: str,
    files: dict[str, Any],
    data: dict[str, Any],
) -> dict[str, Any]:
    client = await get_http_client()
    response = await client.post(
        f"{GROQ_BASE}/audio/transcriptions",
        headers=_build_auth_headers(api_key, json_payload=False),
        files=files,
        data=data,
    )
    if response.status_code != 200:
        raise HTTPException(status_code=response.status_code, detail=response.text)
    return response.json()


async def iter_groq_chat_stream(
    api_key: str,
    payload: dict[str, Any],
) -> AsyncGenerator[str, None]:
    client = await get_http_client()
    async with client.stream(
        "POST",
        f"{GROQ_BASE}/chat/completions",
        headers=_build_auth_headers(api_key),
        json=payload,
    ) as response:
        if response.status_code != 200:
            detail = await response.aread()
            raise HTTPException(status_code=response.status_code, detail=detail.decode("utf-8", errors="replace"))

        async for line in response.aiter_lines():
            if line.startswith("data: "):
                yield f"{line}\n\n"
