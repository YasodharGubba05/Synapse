import React, { useEffect, useState } from 'react';
import { deleteHistorySession, fetchHistory, fetchHistorySession, updateSessionTitle } from '../api';
import { AVAILABLE_PLAYBOOKS } from '../sessionSettings';

const CloseIcon = () => (
  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>
);
const TrashIcon = () => (
  <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round"><polyline points="3 6 5 6 21 6"/><path d="M19 6l-1 14a2 2 0 01-2 2H8a2 2 0 01-2-2L5 6"/></svg>
);
const EditIcon = () => (
  <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round"><path d="M11 4H4a2 2 0 00-2 2v14a2 2 0 002 2h14a2 2 0 002-2v-7"/><path d="M18.5 2.5a2.121 2.121 0 013 3L12 15l-4 1 1-4 9.5-9.5z"/></svg>
);

export default function HistorySidebar({ open, onClose, onLoadSession }) {
  const [sessions, setSessions] = useState([]);
  const [loading, setLoading] = useState(false);
  const [editingId, setEditingId] = useState(null);
  const [editTitle, setEditTitle] = useState('');

  useEffect(() => {
    if (!open) return;
    setLoading(true);
    fetchHistory()
      .then(data => setSessions(Array.isArray(data) ? data : []))
      .catch(() => setSessions([]))
      .finally(() => setLoading(false));
  }, [open]);

  const handleDelete = async (id, e) => {
    e.stopPropagation();
    await deleteHistorySession(id).catch(() => {});
    setSessions(prev => prev.filter(s => s.id !== id));
  };

  const handleEditSave = async (id, e) => {
    e.stopPropagation();
    if (!editTitle.trim()) { setEditingId(null); return; }
    await updateSessionTitle(id, editTitle.trim()).catch(() => {});
    setSessions(prev => prev.map(s => s.id === id ? { ...s, title: editTitle.trim() } : s));
    setEditingId(null);
  };

  const handleLoad = async (id) => {
    try {
      const data = await fetchHistorySession(id);
      onLoadSession(data);
      onClose();
    } catch { /* ignore */ }
  };

  const getPlaybookIcon = (playbook) => AVAILABLE_PLAYBOOKS.find(p => p.value === playbook)?.icon || '🎯';

  if (!open) return null;

  return (
    <div style={s.backdrop} onClick={onClose}>
      <div style={s.sidebar} onClick={e => e.stopPropagation()}>
        <div style={s.header}>
          <span style={s.title}>Meeting History</span>
          <button style={s.closeBtn} onClick={onClose}><CloseIcon /></button>
        </div>

        <div style={s.body} className="scrollable">
          {loading && <div style={s.empty}>Loading...</div>}
          {!loading && sessions.length === 0 && (
            <div style={s.empty}>No saved sessions yet. Start a meeting to record one.</div>
          )}
          {!loading && sessions.map(session => (
            <div key={session.id} style={s.sessionCard} onClick={() => handleLoad(session.id)}>
              <div style={s.cardTop}>
                <span style={s.playbookIcon}>{getPlaybookIcon(session.playbook)}</span>
                {editingId === session.id ? (
                  <input
                    style={s.editInput}
                    value={editTitle}
                    autoFocus
                    onClick={e => e.stopPropagation()}
                    onChange={e => setEditTitle(e.target.value)}
                    onKeyDown={e => { if (e.key === 'Enter') handleEditSave(session.id, e); if (e.key === 'Escape') setEditingId(null); }}
                  />
                ) : (
                  <span style={s.sessionTitle}>{session.title}</span>
                )}
                <div style={s.cardActions} onClick={e => e.stopPropagation()}>
                  <button style={s.iconBtn} title="Rename" onClick={e => { e.stopPropagation(); setEditingId(session.id); setEditTitle(session.title); }}>
                    <EditIcon />
                  </button>
                  <button style={s.iconBtn} title="Delete" onClick={e => handleDelete(session.id, e)}>
                    <TrashIcon />
                  </button>
                </div>
              </div>
              <div style={s.cardMeta}>
                <span>{new Date(session.started_at).toLocaleDateString()} {new Date(session.started_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}</span>
                <span>{session.transcript_count} entries · {session.action_item_count} actions</span>
              </div>
              <div style={{ ...s.statusDot, background: session.status === 'active' ? '#10B981' : 'var(--text-3)' }}>
                {session.status}
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

const s = {
  backdrop: { position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.6)', backdropFilter: 'blur(4px)', zIndex: 150, display: 'flex', alignItems: 'stretch' },
  sidebar: { width: 340, background: 'var(--surface)', borderRight: '1px solid var(--border-bright)', display: 'flex', flexDirection: 'column', height: '100%' },
  header: { padding: '18px 20px', borderBottom: '1px solid var(--border)', display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexShrink: 0 },
  title: { fontFamily: 'var(--font-head)', fontSize: 16, fontWeight: 700, color: 'var(--text-1)' },
  closeBtn: { background: 'transparent', border: 'none', cursor: 'pointer', color: 'var(--text-3)', display: 'flex', padding: 4 },
  body: { flex: 1, overflowY: 'auto', padding: '12px 16px', display: 'flex', flexDirection: 'column', gap: 10 },
  empty: { fontSize: 13, color: 'var(--text-3)', textAlign: 'center', marginTop: 20 },
  sessionCard: { background: 'var(--surface-3)', border: '1px solid var(--border)', borderRadius: 'var(--r-lg)', padding: '12px 14px', cursor: 'pointer', transition: 'all 0.2s', position: 'relative' },
  cardTop: { display: 'flex', alignItems: 'center', gap: 8, marginBottom: 6 },
  playbookIcon: { fontSize: 16, flexShrink: 0 },
  sessionTitle: { flex: 1, fontSize: 13, fontWeight: 600, color: 'var(--text-1)', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' },
  cardActions: { display: 'flex', gap: 4 },
  iconBtn: { background: 'transparent', border: 'none', cursor: 'pointer', color: 'var(--text-3)', padding: 4, borderRadius: 4, display: 'flex', alignItems: 'center' },
  cardMeta: { display: 'flex', justifyContent: 'space-between', fontSize: 10, color: 'var(--text-3)', fontWeight: 500 },
  statusDot: { position: 'absolute', top: 10, right: 10, fontSize: 8, fontWeight: 700, textTransform: 'uppercase', color: '#fff', padding: '2px 6px', borderRadius: 'var(--r-sm)', letterSpacing: '0.08em' },
  editInput: { flex: 1, background: 'var(--surface)', border: '1px solid var(--brand)', borderRadius: 6, padding: '3px 8px', fontSize: 13, color: 'var(--text-1)', outline: 'none', fontFamily: 'var(--font-body)' },
};
