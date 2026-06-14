export const SETTINGS_STORAGE_KEY = 'synapse_session_settings';

export const AVAILABLE_MODELS = [
  { value: 'llama-3.3-70b-versatile', label: 'Llama 3.3 70B (Best quality)' },
  { value: 'llama-3.1-8b-instant', label: 'Llama 3.1 8B (Fast)' },
  { value: 'mixtral-8x7b-32768', label: 'Mixtral 8x7B (Balanced)' },
  { value: 'gemma2-9b-it', label: 'Gemma 2 9B (Efficient)' },
];

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
  selectedModel: 'llama-3.3-70b-versatile',
  playbook: 'general',
  theme: 'dark',
  suggestionsPrompt: '',
  detailPrompt: '',
  chatPrompt: '',
};

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
    selectedModel: settings?.selectedModel || DEFAULT_SESSION_SETTINGS.selectedModel,
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
