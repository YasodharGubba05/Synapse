import React, { useEffect, useState } from 'react';
import { AVAILABLE_MODELS, AVAILABLE_PLAYBOOKS, DEFAULT_SESSION_SETTINGS, normalizeSessionSettings } from '../sessionSettings';
import { useAuth } from '../authContext';
import { fetchAvailableModels } from '../api';

// ── Icons ─────────────────────────────────────────────────────────────────────

const SunIcon = () => (
  <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <circle cx="12" cy="12" r="5"/><line x1="12" y1="1" x2="12" y2="3"/><line x1="12" y1="21" x2="12" y2="23"/>
    <line x1="4.22" y1="4.22" x2="5.64" y2="5.64"/><line x1="18.36" y1="18.36" x2="19.78" y2="19.78"/>
    <line x1="1" y1="12" x2="3" y2="12"/><line x1="21" y1="12" x2="23" y2="12"/>
    <line x1="4.22" y1="19.78" x2="5.64" y2="18.36"/><line x1="18.36" y1="5.64" x2="19.78" y2="4.22"/>
  </svg>
);
const MoonIcon = () => (
  <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"/>
  </svg>
);
const ExportIcon = () => (
  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" y1="15" x2="12" y2="3"/>
  </svg>
);
const SettingsIcon = () => (
  <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <circle cx="12" cy="12" r="3"/>
    <path d="M19.4 15a1.65 1.65 0 00.33 1.82l.06.06a2 2 0 010 2.83 2 2 0 01-2.83 0l-.06-.06a1.65 1.65 0 00-1.82-.33 1.65 1.65 0 00-1 1.51V21a2 2 0 01-4 0v-.09A1.65 1.65 0 009 19.4a1.65 1.65 0 00-1.82.33l-.06.06a2 2 0 01-2.83-2.83l.06-.06A1.65 1.65 0 004.68 15a1.65 1.65 0 00-1.51-1H3a2 2 0 010-4h.09A1.65 1.65 0 004.6 9a1.65 1.65 0 00-.33-1.82l-.06-.06a2 2 0 012.83-2.83l.06.06A1.65 1.65 0 009 4.68a1.65 1.65 0 001-1.51V3a2 2 0 014 0v.09a1.65 1.65 0 001 1.51 1.65 1.65 0 001.82-.33l.06-.06a2 2 0 012.83 2.83l-.06.06A1.65 1.65 0 0019.4 9a1.65 1.65 0 001.51 1H21a2 2 0 010 4h-.09a1.65 1.65 0 00-1.51 1z"/>
  </svg>
);
const LogoutIcon = () => (
  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4"/><polyline points="16 17 21 12 16 7"/><line x1="21" y1="12" x2="9" y2="12"/>
  </svg>
);
const HistoryIcon = () => (
  <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <polyline points="1 4 1 10 7 10"/><path d="M3.51 15a9 9 0 1 0 .49-3.45"/>
  </svg>
);

// ── Settings Modal ────────────────────────────────────────────────────────────

function SettingsModal({ initialSettings, onClose, onSave }) {
  const [draft, setDraft] = useState(() => normalizeSessionSettings(initialSettings));
  const [models, setModels] = useState(AVAILABLE_MODELS);
  const update = (field, value) => setDraft(prev => ({ ...prev, [field]: value }));

  // Ask Groq what this key can actually use. Model IDs get retired, and a
  // retired one returns 404 on every request, so a hardcoded list goes stale.
  // Falls back silently to the built-in list when the key is absent or invalid.
  useEffect(() => {
    let cancelled = false;
    if (!draft.apiKey) return undefined;
    fetchAvailableModels()
      .then(data => {
        if (!cancelled && Array.isArray(data?.models) && data.models.length) {
          setModels(data.models);
        }
      })
      .catch(() => {});
    return () => { cancelled = true; };
    // Only re-run when a key is first supplied, not on every keystroke.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [Boolean(draft.apiKey)]);

  return (
    <div style={s.backdrop} onClick={onClose}>
      <div style={s.card} onClick={e => e.stopPropagation()}>
        <div style={s.cardHeader}>
          <span style={s.cardTitle}>Settings</span>
          <span style={s.cardSub}>Stored only for this browser session</span>
        </div>

        <div style={s.fieldGroup}>
          <label style={s.label}>Groq API Key</label>
          <input type="password" value={draft.apiKey} onChange={e => update('apiKey', e.target.value)}
            placeholder="gsk_..." style={s.input} />
        </div>

        <div style={s.row}>
          <div style={{ ...s.fieldGroup, flex: 1 }}>
            <label style={s.label}>LLM Model</label>
            <select value={draft.selectedModel} onChange={e => update('selectedModel', e.target.value)} style={s.select}>
              {models.map(m => <option key={m.value} value={m.value}>{m.label}</option>)}
              {!models.some(m => m.value === draft.selectedModel) && (
                <option value={draft.selectedModel}>{draft.selectedModel}</option>
              )}
            </select>
          </div>
          <div style={{ ...s.fieldGroup, flex: 1 }}>
            <label style={s.label}>Active Playbook</label>
            <select value={draft.playbook} onChange={e => update('playbook', e.target.value)} style={s.select}>
              {AVAILABLE_PLAYBOOKS.map(p => <option key={p.value} value={p.value}>{p.icon} {p.label}</option>)}
            </select>
          </div>
        </div>

        <div style={s.fieldGroup}>
          <label style={s.label}>Meeting Memory / Prep Notes</label>
          <textarea value={draft.meetingMemory} onChange={e => update('meetingMemory', e.target.value)}
            placeholder="Paste agenda, prior notes, context..." style={s.textarea} />
        </div>

        <div style={s.fieldGroup}>
          <label style={s.label}>Custom Suggestions Prompt (optional)</label>
          <textarea value={draft.suggestionsPrompt} onChange={e => update('suggestionsPrompt', e.target.value)}
            placeholder="Leave blank to use the selected playbook default..." style={{ ...s.textarea, minHeight: 80 }} />
        </div>

        <div style={s.modalActions}>
          <button style={s.btnSecondary} onClick={onClose}>Cancel</button>
          <button style={s.btnSecondary} onClick={() => { const c = { ...draft, apiKey: '' }; setDraft(c); onSave(c); }}>Clear Key</button>
          <button style={s.btnSecondary} onClick={() => setDraft({ ...DEFAULT_SESSION_SETTINGS })}>Reset</button>
          <button style={s.btnPrimary} onClick={() => { onSave(draft); onClose(); }}>Save Settings</button>
        </div>
      </div>
    </div>
  );
}

// ── Navbar ────────────────────────────────────────────────────────────────────

export default function Navbar({ settings, onSaveSettings, onExportSession, canExport, onToggleHistory }) {
  const [settingsOpen, setSettingsOpen] = useState(false);
  const [signingOut, setSigningOut] = useState(false);
  const { user, logout } = useAuth();

  const handleLogout = async () => {
    setSigningOut(true);
    try {
      await logout();
    } finally {
      setSigningOut(false);
    }
  };

  const handlePlaybookChange = (value) => {
    onSaveSettings({ ...settings, playbook: value });
  };

  const handleThemeToggle = () => {
    const next = settings.theme === 'dark' ? 'light' : 'dark';
    onSaveSettings({ ...settings, theme: next });
  };

  return (
    <>
      <nav style={s.navbar}>
        {/* Brand */}
        <div style={s.brand}>
          <div style={s.brandLogo}>
            <span style={s.brandIcon}>⚡</span>
          </div>
          <div>
            <span style={s.brandName}>Synapse</span>
            <span style={s.brandTag}>Live Intelligence</span>
          </div>
        </div>

        {/* Playbook Selector */}
        <div style={s.playbookWrap}>
          {AVAILABLE_PLAYBOOKS.map(p => (
            <button
              key={p.value}
              style={{ ...s.playbookBtn, ...(settings.playbook === p.value ? s.playbookBtnActive : {}) }}
              onClick={() => handlePlaybookChange(p.value)}
              title={p.label}
            >
              <span>{p.icon}</span>
              <span style={s.playbookLabel}>{p.label}</span>
            </button>
          ))}
        </div>

        <div style={{ flex: 1 }} />

        {/* Actions */}
        <div style={s.actions}>
          <button className="btn-ghost" onClick={onToggleHistory} title="Meeting History" style={s.iconBtn}>
            <HistoryIcon />
          </button>
          <button className="btn-ghost" onClick={handleThemeToggle} title="Toggle theme" style={s.iconBtn}>
            {settings.theme === 'dark' ? <SunIcon /> : <MoonIcon />}
          </button>
          <button className="btn-ghost" style={{ ...s.iconBtn, opacity: canExport ? 1 : 0.35 }}
            onClick={onExportSession} disabled={!canExport} title="Export session">
            <ExportIcon />
            <span>Export</span>
          </button>
          <button className="btn-ghost" onClick={() => setSettingsOpen(true)} style={s.iconBtn}>
            <SettingsIcon />
            <span>Settings</span>
          </button>

          {user && (
            <div style={s.account}>
              <span style={s.avatar} title={user.email}>
                {(user.full_name || user.email || '?').trim().charAt(0).toUpperCase()}
              </span>
              <span style={s.accountEmail}>{user.email}</span>
              <button
                className="btn-ghost"
                onClick={handleLogout}
                disabled={signingOut}
                title="Sign out"
                style={{ ...s.iconBtn, opacity: signingOut ? 0.5 : 1 }}
              >
                <LogoutIcon />
                <span>{signingOut ? 'Signing out…' : 'Sign out'}</span>
              </button>
            </div>
          )}
        </div>
      </nav>

      {settingsOpen && (
        <SettingsModal initialSettings={settings} onClose={() => setSettingsOpen(false)} onSave={onSaveSettings} />
      )}
    </>
  );
}

const s = {
  navbar: {
    background: 'var(--glass)',
    backdropFilter: 'saturate(180%) blur(20px)',
    WebkitBackdropFilter: 'saturate(180%) blur(20px)',
    borderBottom: '1px solid var(--border)',
    boxShadow: 'var(--highlight)',
    minHeight: 56,
    padding: '0 20px',
    display: 'flex',
    alignItems: 'center',
    gap: 12,
    position: 'sticky',
    top: 0,
    zIndex: 100,
    flexShrink: 0,
  },
  brand: { display: 'flex', alignItems: 'center', gap: 10, flexShrink: 0 },
  brandLogo: {
    width: 30, height: 30,
    background: 'linear-gradient(180deg, var(--brand) 0%, var(--brand-deep) 100%)',
    border: '1px solid rgba(255,255,255,0.14)',
    boxShadow: 'var(--highlight-strong), 0 2px 8px -2px rgba(92,108,232,0.5)',
    borderRadius: 'var(--r-md)',
    display: 'flex', alignItems: 'center', justifyContent: 'center',
  },
  brandIcon: { fontSize: 15 },
  brandName: { display: 'block', fontFamily: 'var(--font-head)', fontSize: 15, fontWeight: 700, letterSpacing: '-0.01em', color: 'var(--text-1)', lineHeight: 1.15 },
  brandTag: { display: 'block', fontSize: 9, fontWeight: 600, letterSpacing: '0.12em', textTransform: 'uppercase', color: 'var(--text-3)', marginTop: 1 },
  playbookWrap: { display: 'flex', alignItems: 'center', gap: 2, background: 'var(--fill-sunken)', padding: '3px', borderRadius: 'var(--r-md)', border: '1px solid var(--border)', boxShadow: 'inset 0 1px 2px rgba(0,0,0,0.3)' },
  playbookBtn: {
    display: 'flex', alignItems: 'center', gap: 5,
    padding: '5px 9px',
    borderRadius: 'var(--r-sm)',
    border: 'none',
    background: 'transparent',
    color: 'var(--text-3)',
    fontSize: 12, fontWeight: 500, fontFamily: 'var(--font-body)',
    cursor: 'pointer',
    transition: 'all 0.2s',
    whiteSpace: 'nowrap',
  },
  playbookBtnActive: {
    background: 'var(--fill-raised)',
    color: 'var(--text-1)',
    boxShadow: 'var(--highlight), 0 1px 2px rgba(0,0,0,0.35)',
  },
  playbookLabel: { display: 'none' },
  actions: { display: 'flex', alignItems: 'center', gap: 6 },
  iconBtn: { padding: '7px 12px', fontSize: 12, gap: 5 },
  account: {
    display: 'flex', alignItems: 'center', gap: 8,
    marginLeft: 6, paddingLeft: 10,
    borderLeft: '1px solid var(--border)',
  },
  avatar: {
    width: 24, height: 24, borderRadius: 'var(--r-sm)',
    background: 'linear-gradient(180deg, var(--brand) 0%, var(--brand-deep) 100%)',
    border: '1px solid rgba(255,255,255,0.14)',
    boxShadow: 'var(--highlight)',
    color: '#fff', fontSize: 10.5, fontWeight: 700,
    display: 'flex', alignItems: 'center', justifyContent: 'center',
    flexShrink: 0,
  },
  accountEmail: {
    fontSize: 11.5, color: 'var(--text-2)', fontWeight: 500,
    maxWidth: 150, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap',
  },
  // Modal styles
  backdrop: {
    position: 'fixed', inset: 0,
    background: 'rgba(0,0,0,0.7)',
    backdropFilter: 'blur(6px)',
    display: 'flex', alignItems: 'center', justifyContent: 'center',
    padding: 24, zIndex: 200,
  },
  card: {
    background: 'var(--fill-raised)',
    border: '1px solid var(--border-bright)',
    borderRadius: 'var(--r-xl)',
    width: 'min(680px, calc(100vw - 32px))',
    maxHeight: 'calc(100vh - 48px)',
    overflowY: 'auto',
    padding: 28,
    boxShadow: 'var(--highlight-strong), var(--shadow-lg)',
  },
  cardHeader: { marginBottom: 24 },
  cardTitle: { display: 'block', fontFamily: 'var(--font-head)', fontSize: 20, fontWeight: 700, color: 'var(--text-1)' },
  cardSub: { display: 'block', fontSize: 12, color: 'var(--text-3)', marginTop: 4 },
  fieldGroup: { display: 'flex', flexDirection: 'column', gap: 8, marginBottom: 18 },
  row: { display: 'flex', gap: 14, marginBottom: 0 },
  label: { fontSize: 11, fontWeight: 600, color: 'var(--text-3)', letterSpacing: '0.07em', textTransform: 'uppercase' },
  input: {
    width: '100%', border: '1px solid var(--border-bright)', borderRadius: 'var(--r-md)',
    padding: '10px 13px', fontSize: 13, color: 'var(--text-1)',
    background: 'var(--fill-sunken)', outline: 'none', fontFamily: 'var(--font-body)',
    boxShadow: 'inset 0 1px 2px rgba(0,0,0,0.25)',
  },
  select: {
    width: '100%', border: '1px solid var(--border-bright)', borderRadius: 'var(--r-md)',
    padding: '10px 13px', fontSize: 13, color: 'var(--text-1)',
    background: 'var(--fill-sunken)', outline: 'none', fontFamily: 'var(--font-body)', cursor: 'pointer',
    boxShadow: 'inset 0 1px 2px rgba(0,0,0,0.25)',
  },
  textarea: {
    width: '100%', minHeight: 100, border: '1px solid var(--border-bright)', borderRadius: 'var(--r-md)',
    padding: 12, fontSize: 13, color: 'var(--text-1)',
    background: 'var(--fill-sunken)', outline: 'none', fontFamily: 'var(--font-body)',
    boxShadow: 'inset 0 1px 2px rgba(0,0,0,0.25)',
    resize: 'vertical', lineHeight: 1.5,
  },
  modalActions: { marginTop: 24, display: 'flex', flexWrap: 'wrap', justifyContent: 'flex-end', gap: 10 },
  btnSecondary: {
    border: '1px solid var(--border-bright)', background: 'transparent', color: 'var(--text-2)',
    borderRadius: 'var(--r-md)', padding: '8px 14px', cursor: 'pointer', fontSize: 'var(--fs-sm)', fontWeight: 500, fontFamily: 'var(--font-body)',
  },
  btnPrimary: {
    border: 'none', background: 'var(--action-fill)', color: 'var(--action-text)',
    boxShadow: '0 1px 2px rgba(0,0,0,0.3)',
    borderRadius: 'var(--r-md)', padding: '8px 18px', cursor: 'pointer', fontSize: 'var(--fs-sm)', fontWeight: 600, fontFamily: 'var(--font-body)',
  },
};
