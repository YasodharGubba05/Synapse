export const SETTINGS_STORAGE_KEY = 'synapse_session_settings';

export const AVAILABLE_MODELS = [
  { value: 'openai/gpt-oss-120b', label: 'GPT-OSS 120B (Best quality)' },
  { value: 'openai/gpt-oss-20b', label: 'GPT-OSS 20B (Fast)' },
];

/**
 * Model IDs Groq has decommissioned. A retired ID returns 404 rather than
 * falling back to anything, so a value saved in a browser before the
 * retirement would keep breaking every request until it is migrated.
 */
const RETIRED_MODELS = new Set([
  'llama-3.3-70b-versatile',
  'llama-3.1-8b-instant',
  'mixtral-8x7b-32768',
  'gemma2-9b-it',
  'mistral-saba-24b',
  'distil-whisper-large-v3-en',
]);

export const AVAILABLE_PLAYBOOKS = [
  { value: 'general', label: 'General Meeting', icon: '🎯' },
  { value: 'standup', label: 'Daily Standup', icon: '⚡' },
  { value: 'design', label: 'Product Design', icon: '🛠️' },
  { value: 'sales', label: 'Sales Discovery', icon: '💼' },
];

export const DEFAULT_SESSION_SETTINGS = {
  apiKey: '',
  meetingMemory: '',
  suggestionsContextWindow: 800,
  detailContextWindow: 3000,
  chatContextWindow: 3000,
  selectedModel: 'openai/gpt-oss-120b',
  playbook: 'general',
  theme: 'dark',
  suggestionsPrompt: '',
  detailPrompt: '',
  chatPrompt: '',
};

/** Fall back to the default when the saved model has been retired. */
export function normalizeModel(value) {
  const model = String(value || '').trim();
  if (!model || RETIRED_MODELS.has(model)) return DEFAULT_SESSION_SETTINGS.selectedModel;
  return model;
}

function parseInteger(value, fallback) {
  const parsed = Number.parseInt(value, 10);
  return Number.isFinite(parsed) && parsed > 0 ? parsed : fallback;
}

export function normalizeSessionSettings(settings) {
  return {
    ...DEFAULT_SESSION_SETTINGS,
    ...settings,
    apiKey: String(settings?.apiKey ?? '').trim(),
    meetingMemory: String(settings?.meetingMemory ?? ''),
    suggestionsContextWindow: parseInteger(settings?.suggestionsContextWindow, 800),
    detailContextWindow: parseInteger(settings?.detailContextWindow, 3000),
    chatContextWindow: parseInteger(settings?.chatContextWindow, 3000),
    selectedModel: normalizeModel(settings?.selectedModel),
    playbook: settings?.playbook || DEFAULT_SESSION_SETTINGS.playbook,
    theme: settings?.theme || 'dark',
    suggestionsPrompt: String(settings?.suggestionsPrompt ?? ''),
    detailPrompt: String(settings?.detailPrompt ?? ''),
    chatPrompt: String(settings?.chatPrompt ?? ''),
  };
}

export function loadSessionSettings() {
  try {
    let raw = sessionStorage.getItem(SETTINGS_STORAGE_KEY);
    if (!raw) {
      const oldRaw = sessionStorage.getItem('meetscribe_session_settings');
      if (oldRaw) {
        const parsed = JSON.parse(oldRaw);
        const normalized = normalizeSessionSettings(parsed);
        sessionStorage.setItem(SETTINGS_STORAGE_KEY, JSON.stringify(normalized));
        return normalized;
      }
      return { ...DEFAULT_SESSION_SETTINGS };
    }
    return normalizeSessionSettings(JSON.parse(raw));
  } catch {
    return { ...DEFAULT_SESSION_SETTINGS };
  }
}

export function saveSessionSettings(settings) {
  const normalized = normalizeSessionSettings(settings);
  sessionStorage.setItem(SETTINGS_STORAGE_KEY, JSON.stringify(normalized));
  return normalized;
}

export function formatSessionTimestamp(date = new Date()) {
  return {
    iso: date.toISOString(),
    label: date.toLocaleTimeString([], { hour12: false, hour: '2-digit', minute: '2-digit', second: '2-digit' }),
  };
}
