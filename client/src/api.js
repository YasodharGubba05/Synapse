const RAW_API_BASE = (import.meta.env.VITE_API_BASE || '/api').trim();
const API_BASE = RAW_API_BASE.endsWith('/') ? RAW_API_BASE.slice(0, -1) : RAW_API_BASE;
const SETTINGS_STORAGE_KEY = 'synapse_session_settings';
const CSRF_COOKIE = 'synapse_csrf';

/** Raised when the session is gone and a refresh could not recover it. */
export class SessionExpiredError extends Error {
  constructor(message = 'Your session has expired. Please sign in again.') {
    super(message);
    this.name = 'SessionExpiredError';
    this.status = 401;
  }
}

/** Fired when the backend rejects us for good; AuthProvider listens for it. */
export const SESSION_EXPIRED_EVENT = 'synapse:session-expired';

function announceSessionExpired() {
  if (typeof window !== 'undefined') {
    window.dispatchEvent(new CustomEvent(SESSION_EXPIRED_EVENT));
  }
}

// ── Credentials ───────────────────────────────────────────────────────────────
// The Groq API key stays in sessionStorage and is injected per request, exactly
// as before. Authentication is entirely separate: HTTP-only cookies the browser
// attaches itself, plus the readable CSRF cookie echoed back in a header.

function getGroqApiKey() {
  try {
    const stored = sessionStorage.getItem(SETTINGS_STORAGE_KEY);
    if (!stored) return '';
    return JSON.parse(stored)?.apiKey || '';
  } catch { return ''; }
}

function getCsrfToken() {
  try {
    const match = document.cookie.match(new RegExp(`(?:^|; )${CSRF_COOKIE}=([^;]*)`));
    return match ? decodeURIComponent(match[1]) : '';
  } catch { return ''; }
}

function buildHeaders(includeContentType = true) {
  const headers = { 'X-Groq-API-Key': getGroqApiKey() };
  if (includeContentType) headers['Content-Type'] = 'application/json';
  const csrf = getCsrfToken();
  if (csrf) headers['X-CSRF-Token'] = csrf;
  return headers;
}

// ── Transport ─────────────────────────────────────────────────────────────────

let refreshInFlight = null;

/** Refresh the access cookie. Concurrent callers share one request. */
function refreshSession() {
  if (!refreshInFlight) {
    refreshInFlight = fetch(`${API_BASE}/auth/refresh`, {
      method: 'POST',
      credentials: 'include',
      headers: buildHeaders(true),
    })
      .then(response => response.ok)
      .catch(() => false)
      .finally(() => { refreshInFlight = null; });
  }
  return refreshInFlight;
}

/**
 * fetch with cookies attached. On a 401 it transparently refreshes the session
 * once and replays the request, so a short-lived access token expiring mid-use
 * is invisible to the user. `skipRefresh` is used by the auth calls themselves.
 */
async function authedFetch(path, options = {}, { skipRefresh = false } = {}) {
  const send = () => fetch(`${API_BASE}${path}`, { ...options, credentials: 'include' });

  let response = await send();
  // Only try to refresh when a CSRF cookie exists: without one we were
  // never signed in, so /auth/refresh would just 403 for every anonymous
  // visitor on first paint.
  if (response.status === 401 && !skipRefresh && getCsrfToken()) {
    const refreshed = await refreshSession();
    if (refreshed) {
      // Rebuild headers: refreshing rotated the CSRF cookie.
      const retryOptions = { ...options };
      if (retryOptions.headers) {
        const hadContentType = Boolean(retryOptions.headers['Content-Type']);
        retryOptions.headers = { ...buildHeaders(hadContentType), ...stripAuthHeaders(retryOptions.headers) };
      }
      response = await fetch(`${API_BASE}${path}`, { ...retryOptions, credentials: 'include' });
    }
    if (response.status === 401) {
      announceSessionExpired();
      throw new SessionExpiredError();
    }
  }
  return response;
}

/** Drop the headers that must be recomputed after a refresh. */
function stripAuthHeaders(headers) {
  const copy = { ...headers };
  delete copy['X-CSRF-Token'];
  delete copy['X-Groq-API-Key'];
  return copy;
}

async function failureMessage(response, fallback) {
  const text = await response.text().catch(() => '');
  if (!text) return fallback;
  try {
    const parsed = JSON.parse(text);
    if (typeof parsed.detail === 'string') return parsed.detail;
    if (Array.isArray(parsed.detail)) {
      return parsed.detail.map(d => d.message || d.msg).filter(Boolean).join('; ') || fallback;
    }
  } catch { /* not JSON */ }
  return text || fallback;
}

// ── Authentication ────────────────────────────────────────────────────────────

export async function registerAccount({ email, password, fullName }) {
  const body = { email, password };
  if (fullName) body.full_name = fullName;
  const response = await authedFetch('/auth/register', {
    method: 'POST', headers: buildHeaders(true), body: JSON.stringify(body),
  }, { skipRefresh: true });
  if (!response.ok) throw new Error(await failureMessage(response, 'Registration failed'));
  return response.json();
}

export async function loginAccount({ email, password }) {
  const response = await authedFetch('/auth/login', {
    method: 'POST', headers: buildHeaders(true), body: JSON.stringify({ email, password }),
  }, { skipRefresh: true });
  if (!response.ok) throw new Error(await failureMessage(response, 'Login failed'));
  return response.json();
}

export async function logoutAccount() {
  const response = await authedFetch('/auth/logout', {
    method: 'POST', headers: buildHeaders(true),
  }, { skipRefresh: true });
  if (!response.ok && response.status !== 401) {
    throw new Error(await failureMessage(response, 'Logout failed'));
  }
  return { ok: true };
}

/** Resolve the signed-in user from cookies, or null when not signed in. */
export async function fetchCurrentUser() {
  const response = await authedFetch('/auth/me', { headers: buildHeaders(false) });
  if (response.status === 401) return null;
  if (!response.ok) throw new Error(await failureMessage(response, 'Could not load your account'));
  return response.json();
}

export async function changePassword({ currentPassword, newPassword }) {
  const response = await authedFetch('/auth/password', {
    method: 'POST',
    headers: buildHeaders(true),
    body: JSON.stringify({ current_password: currentPassword, new_password: newPassword }),
  });
  if (!response.ok) throw new Error(await failureMessage(response, 'Password change failed'));
  return response.json();
}

function getAudioExtensionFromMimeType(mimeType) {
  const n = (mimeType || '').split(';')[0].trim().toLowerCase();
  if (n === 'audio/webm') return 'webm';
  if (n === 'audio/mp4' || n === 'audio/x-m4a') return 'm4a';
  if (n === 'audio/wav' || n === 'audio/x-wav') return 'wav';
  if (n === 'audio/mpeg') return 'mp3';
  if (n === 'audio/ogg') return 'ogg';
  return 'webm';
}

export async function transcribeAudioBlob(audioBlob) {
  const formData = new FormData();
  const extension = getAudioExtensionFromMimeType(audioBlob?.type);
  formData.append('audio_file', audioBlob, `meeting-audio.${extension}`);
  const response = await authedFetch('/transcribe', { method: 'POST', headers: buildHeaders(false), body: formData });
  if (!response.ok) {
    const detail = await response.text().catch(() => '');
    throw new Error(`Transcription failed (${response.status}): ${detail}`);
  }
  const data = await response.json();
  // Surface any error message from the backend (e.g. Groq API rejection reason)
  if (data.error) console.warn('[Synapse] Backend transcription error:', data.error);
  return data;
}

export async function fetchSuggestions(payload) {
  const response = await authedFetch('/suggestions', {
    method: 'POST', headers: buildHeaders(true), body: JSON.stringify(payload),
  });
  if (!response.ok) throw new Error(await failureMessage(response, `Suggestions failed (${response.status})`));
  return response.json();
}

export async function fetchIntelligence(payload) {
  const response = await authedFetch('/intelligence', {
    method: 'POST', headers: buildHeaders(true), body: JSON.stringify(payload),
  });
  if (!response.ok) throw new Error(await failureMessage(response, `Intelligence failed (${response.status})`));
  return response.json();
}

/** Chat models the signed-in user's Groq key can actually use. */
export async function fetchAvailableModels() {
  const response = await authedFetch('/models', { headers: buildHeaders(false) });
  if (!response.ok) throw new Error(`Model list failed (${response.status})`);
  return response.json();
}

export async function startMeeting(payload) {
  const response = await authedFetch('/meeting/start', {
    method: 'POST', headers: buildHeaders(true), body: JSON.stringify(payload),
  });
  if (!response.ok) throw new Error(await failureMessage(response, `Meeting start failed (${response.status})`));
  return response.json();
}

export async function endMeeting(payload) {
  const response = await authedFetch('/meeting/end', {
    method: 'POST', headers: buildHeaders(true), body: JSON.stringify(payload),
  });
  if (!response.ok) throw new Error(await failureMessage(response, `Meeting end failed (${response.status})`));
  return response.json();
}

export async function warmupBackend() {
  const response = await fetch(`${API_BASE}/health`, { method: 'GET', credentials: 'include' });
  if (!response.ok) throw new Error(`Backend warm-up failed (${response.status})`);
  return response.json();
}

export async function streamChat(payload, onToken) {
  const response = await authedFetch('/chat', {
    method: 'POST', headers: buildHeaders(true), body: JSON.stringify(payload),
  });
  if (!response.ok) throw new Error(await failureMessage(response, `Chat failed (${response.status})`));
  if (!response.body) throw new Error('Streaming response body is missing.');

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = '';
  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    const chunks = buffer.split('\n\n');
    buffer = chunks.pop() || '';
    for (const chunk of chunks) {
      if (!chunk.startsWith('data: ')) continue;
      const payloadText = chunk.slice(6);
      if (payloadText === '[DONE]') continue;
      try {
        const parsed = JSON.parse(payloadText);
        // The backend emits this when Groq rejects the request mid-stream.
        if (parsed.error) {
          throw new Error(parsed.error.message || `Chat failed (${parsed.error.status})`);
        }
        const token = parsed.choices?.[0]?.delta?.content;
        if (token) onToken(token);
      } catch (err) {
        if (err instanceof Error && err.message) throw err;
        /* ignore unparseable keep-alive frames */
      }
    }
  }
}

// ── History API ───────────────────────────────────────────────────────────────

export async function fetchHistory() {
  const response = await authedFetch('/history', { headers: buildHeaders(false) });
  if (!response.ok) throw new Error(`History fetch failed (${response.status})`);
  return response.json();
}

export async function fetchHistorySession(sessionId) {
  const response = await authedFetch(`/history/${sessionId}`, { headers: buildHeaders(false) });
  if (!response.ok) throw new Error(`Session fetch failed (${response.status})`);
  return response.json();
}

/** Persist one captured transcript segment against its meeting. */
export async function saveTranscriptEntry(sessionId, entry) {
  const response = await authedFetch(`/history/${sessionId}/transcript`, {
    method: 'POST', headers: buildHeaders(true), body: JSON.stringify(entry),
  });
  if (!response.ok) throw new Error(`Transcript save failed (${response.status})`);
  return response.json();
}

export async function deleteHistorySession(sessionId) {
  const response = await authedFetch(`/history/${sessionId}`, { method: 'DELETE', headers: buildHeaders(false) });
  if (!response.ok) throw new Error(`Delete failed (${response.status})`);
  return response.json();
}

export async function updateSessionTitle(sessionId, title) {
  const response = await authedFetch(`/history/${sessionId}/title`, {
    method: 'PUT', headers: buildHeaders(true), body: JSON.stringify({ title }),
  });
  if (!response.ok) throw new Error(`Title update failed (${response.status})`);
  return response.json();
}

export async function patchActionItemStatus(sessionId, itemId, status) {
  const response = await authedFetch(`/history/${sessionId}/actions/${itemId}`, {
    method: 'PATCH', headers: buildHeaders(true), body: JSON.stringify({ status }),
  });
  if (!response.ok) throw new Error(`Action item update failed (${response.status})`);
  return response.json();
}

export async function deleteActionItemApi(sessionId, itemId) {
  const response = await authedFetch(`/history/${sessionId}/actions/${itemId}`, {
    method: 'DELETE', headers: buildHeaders(false),
  });
  if (!response.ok) throw new Error(`Action item delete failed (${response.status})`);
  return response.json();
}

export function exportSessionAsJson(session) {
  const blob = new Blob([JSON.stringify(session, null, 2)], { type: 'application/json' });
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement('a');
  anchor.href = url;
  anchor.download = `synapse-session-${new Date().toISOString().replaceAll(':', '-')}.json`;
  document.body.appendChild(anchor);
  anchor.click();
  anchor.remove();
  URL.revokeObjectURL(url);
}
