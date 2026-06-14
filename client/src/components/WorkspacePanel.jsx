import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { streamChat } from '../api';
import { formatSessionTimestamp } from '../sessionSettings';

// ── Icons ─────────────────────────────────────────────────────────────────────
const SendIcon = () => (
  <svg width="14" height="14" viewBox="0 0 24 24" fill="white"><polygon points="22 2 15 22 11 13 2 9 22 2"/></svg>
);
const CheckIcon = () => (
  <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"><polyline points="20 6 9 17 4 12"/></svg>
);
const TrashIcon = () => (
  <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><polyline points="3 6 5 6 21 6"/><path d="M19 6l-1 14a2 2 0 01-2 2H8a2 2 0 01-2-2L5 6"/><path d="M10 11v6M14 11v6"/></svg>
);
const PlusIcon = () => (
  <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round"><line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/></svg>
);

// ── Sentiment Gauge ───────────────────────────────────────────────────────────
const SENTIMENT_CONFIG = {
  positive:     { color: '#10B981', bg: 'rgba(16,185,129,0.15)', label: 'Positive', icon: '😊' },
  constructive: { color: '#F59E0B', bg: 'rgba(245,158,11,0.15)', label: 'Constructive', icon: '🤝' },
  neutral:      { color: '#94A3B8', bg: 'rgba(148,163,184,0.15)', label: 'Neutral', icon: '😐' },
  conflicted:   { color: '#F43F5E', bg: 'rgba(244,63,94,0.15)', label: 'Conflicted', icon: '⚡' },
};

// ── Markdown renderer (simplified) ───────────────────────────────────────────
function renderAssistant(text) {
  if (!text) return null;
  const lines = text.split('\n');
  const nodes = [];
  let bullets = [];
  const flush = () => {
    if (bullets.length) { nodes.push(<ul key={nodes.length} style={{ margin: '6px 0 10px 16px', padding: 0 }}>{bullets.map((b, i) => <li key={i} style={{ fontSize: 13.5, color: 'var(--text-1)', lineHeight: 1.6, marginBottom: 4 }}>{b}</li>)}</ul>); bullets = []; }
  };
  lines.forEach((line, i) => {
    const trimmed = line.trim();
    if (!trimmed) { flush(); return; }
    const bullet = trimmed.match(/^[-*]\s+(.+)/);
    if (bullet) { bullets.push(bullet[1]); return; }
    flush();
    const bold = trimmed.replace(/\*\*(.+?)\*\*/g, '<b>$1</b>');
    nodes.push(<p key={i} style={{ margin: '0 0 8px', fontSize: 13.5, color: 'var(--text-1)', lineHeight: 1.65 }} dangerouslySetInnerHTML={{ __html: bold }} />);
  });
  flush();
  return nodes;
}

// ── Chat Tab ──────────────────────────────────────────────────────────────────
function ChatTab({ chatMessages, pendingMessage, fullTranscript, hasApiKey, setChatMessages, settings }) {
  const [input, setInput] = useState('');
  const [isSending, setIsSending] = useState(false);
  const bodyRef = useRef(null);
  const lastPendingAtRef = useRef(null);

  const messages = useMemo(() => chatMessages.length > 0 ? chatMessages : [{
    role: 'assistant', text: 'Click a suggestion card or type a question. I answer from the current session transcript and meeting memory.', time: '', isoTime: 'welcome',
  }], [chatMessages]);

  useEffect(() => {
    if (bodyRef.current) bodyRef.current.scrollTop = bodyRef.current.scrollHeight;
  }, [messages]);

  const buildHistory = useCallback(
    () => chatMessages.map(m => ({ role: m.role, content: m.text })).filter(m => m.content.trim()),
    [chatMessages]
  );

  const sendMessage = useCallback(async (text, mode = 'chat') => {
    const trimmed = text.trim();
    if (!trimmed || isSending) return;
    if (!hasApiKey) {
      const ts = formatSessionTimestamp();
      setChatMessages(prev => [...prev, { role: 'assistant', text: 'Add your Groq API key in Settings.', time: ts.label, isoTime: ts.iso }]);
      return;
    }
    const history = buildHistory();
    const ts = formatSessionTimestamp();
    setChatMessages(prev => [...prev,
      { role: 'user', text: trimmed, time: ts.label, isoTime: ts.iso },
      { role: 'assistant', text: '', time: ts.label, isoTime: ts.iso + '-a' },
    ]);
    setIsSending(true);
    try {
      await streamChat({
        message: trimmed, mode, history, full_transcript: fullTranscript,
        meeting_memory: settings.meetingMemory,
        chat_prompt: settings.chatPrompt || undefined,
        detail_prompt: settings.detailPrompt || undefined,
        context_window: mode === 'suggestion' ? settings.detailContextWindow : settings.chatContextWindow,
        session_id: settings.sessionId,
        model: settings.selectedModel,
      }, (token) => {
        setChatMessages(prev => { const next = [...prev]; next[next.length - 1] = { ...next[next.length - 1], text: next[next.length - 1].text + token }; return next; });
      });
    } catch {
      setChatMessages(prev => { const next = [...prev]; next[next.length - 1] = { ...next[next.length - 1], text: 'Chat stream failed. Please try again.' }; return next; });
    } finally {
      setIsSending(false);
    }
  }, [buildHistory, fullTranscript, hasApiKey, isSending, setChatMessages, settings]);

  useEffect(() => {
    if (!pendingMessage || pendingMessage.at === lastPendingAtRef.current) return;
    lastPendingAtRef.current = pendingMessage.at;
    sendMessage(pendingMessage.text, pendingMessage.mode || 'suggestion');
  }, [pendingMessage, sendMessage]);

  return (
    <div style={{ display: 'flex', flexDirection: 'column', flex: 1, minHeight: 0 }}>
      <div ref={bodyRef} style={s.chatBody} className="scrollable">
        {messages.map((msg, i) => {
          const isUser = msg.role === 'user';
          return (
            <div key={`${msg.isoTime}-${i}`} style={{ ...s.bubbleWrap, justifyContent: isUser ? 'flex-end' : 'flex-start' }}>
              <div style={{ ...s.bubble, ...(isUser ? s.bubbleUser : s.bubbleAssistant) }}>
                {isUser ? msg.text : renderAssistant(msg.text)}
                {!msg.text && <span style={{ opacity: 0.4, fontSize: 12 }}>Thinking…</span>}
              </div>
            </div>
          );
        })}
      </div>
      <div style={s.inputArea}>
        <textarea
          style={s.textarea}
          value={input}
          rows={1}
          placeholder="Ask anything about the meeting..."
          onChange={e => setInput(e.target.value)}
          onKeyDown={e => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); const t = input.trim(); if (t) { setInput(''); sendMessage(t, 'chat'); } } }}
        />
        <button
          style={{ ...s.sendBtn, opacity: isSending ? 0.5 : 1 }}
          onClick={() => { const t = input.trim(); if (t) { setInput(''); sendMessage(t, 'chat'); } }}
          disabled={isSending}
        >
          <SendIcon />
        </button>
      </div>
    </div>
  );
}

// ── Workspace Board Tab ───────────────────────────────────────────────────────
function WorkspaceBoard({ actionItems, decisions, sentiment, keywords, onAddAction, onToggleAction, onDeleteAction }) {
  const [newTask, setNewTask] = useState('');
  const sentConf = SENTIMENT_CONFIG[sentiment] || SENTIMENT_CONFIG.neutral;

  const priorityColor = (p) => p === 'high' ? '#F43F5E' : p === 'medium' ? '#F59E0B' : '#10B981';

  return (
    <div style={s.board} className="scrollable">
      {/* Sentiment */}
      <div style={s.section}>
        <div style={s.sectionTitle}>Meeting Tone</div>
        <div style={{ ...s.sentimentBadge, background: sentConf.bg, color: sentConf.color }}>
          <span style={{ fontSize: 18 }}>{sentConf.icon}</span>
          <span style={{ fontWeight: 700, fontSize: 14 }}>{sentConf.label}</span>
        </div>
      </div>

      {/* Keywords */}
      {keywords.length > 0 && (
        <div style={s.section}>
          <div style={s.sectionTitle}>Key Topics</div>
          <div style={s.tagCloud}>
            {keywords.map((k, i) => (
              <span key={i} style={s.keyword}>{k}</span>
            ))}
          </div>
        </div>
      )}

      {/* Decisions */}
      {decisions.length > 0 && (
        <div style={s.section}>
          <div style={s.sectionTitle}>Key Decisions</div>
          {decisions.map((d, i) => (
            <div key={i} style={s.decisionItem}>
              <span style={s.decisionDot}>✓</span>
              <span style={{ fontSize: 13, color: 'var(--text-1)', lineHeight: 1.5 }}>{d}</span>
            </div>
          ))}
        </div>
      )}

      {/* Action Items */}
      <div style={s.section}>
        <div style={s.sectionTitle}>Action Items</div>
        {actionItems.length === 0 && <div style={s.emptyNote}>AI will extract action items as the meeting progresses.</div>}
        {actionItems.map(item => (
          <div key={item.id} style={{ ...s.actionItem, opacity: item.status === 'completed' ? 0.5 : 1 }}>
            <button style={s.checkBtn} onClick={() => onToggleAction(item.id, item.status)}>
              {item.status === 'completed' ? <CheckIcon /> : <span style={s.emptyCheck} />}
            </button>
            <div style={{ flex: 1 }}>
              <span style={{ fontSize: 13, color: 'var(--text-1)', textDecoration: item.status === 'completed' ? 'line-through' : 'none' }}>{item.task}</span>
              <div style={{ display: 'flex', gap: 6, marginTop: 4, alignItems: 'center' }}>
                {item.assignee && <span style={{ fontSize: 10, color: 'var(--text-3)' }}>@{item.assignee}</span>}
                <span style={{ fontSize: 10, color: priorityColor(item.priority), fontWeight: 600, textTransform: 'uppercase' }}>{item.priority}</span>
              </div>
            </div>
            <button style={s.deleteBtn} onClick={() => onDeleteAction(item.id)}><TrashIcon /></button>
          </div>
        ))}
        {/* Add task */}
        <div style={s.addTaskRow}>
          <input
            style={s.addInput}
            placeholder="Add action item..."
            value={newTask}
            onChange={e => setNewTask(e.target.value)}
            onKeyDown={e => { if (e.key === 'Enter' && newTask.trim()) { onAddAction(newTask.trim()); setNewTask(''); } }}
          />
          <button style={s.addBtn} onClick={() => { if (newTask.trim()) { onAddAction(newTask.trim()); setNewTask(''); } }}>
            <PlusIcon />
          </button>
        </div>
      </div>
    </div>
  );
}

// ── WorkspacePanel (combined) ─────────────────────────────────────────────────
export default function WorkspacePanel({
  chatMessages, pendingMessage, fullTranscript, hasApiKey, setChatMessages, settings,
  actionItems, decisions, sentiment, keywords, onAddAction, onToggleAction, onDeleteAction,
}) {
  const [activeTab, setActiveTab] = useState('chat');

  return (
    <div style={s.panel}>
      {/* Tabs */}
      <div style={s.tabs}>
        {[['chat', '💬 Chat'], ['board', '📋 Workspace']].map(([val, label]) => (
          <button key={val} style={{ ...s.tab, ...(activeTab === val ? s.tabActive : {}) }} onClick={() => setActiveTab(val)}>
            {label}
          </button>
        ))}
      </div>

      {activeTab === 'chat' ? (
        <ChatTab
          chatMessages={chatMessages} pendingMessage={pendingMessage}
          fullTranscript={fullTranscript} hasApiKey={hasApiKey}
          setChatMessages={setChatMessages} settings={settings}
        />
      ) : (
        <WorkspaceBoard
          actionItems={actionItems} decisions={decisions}
          sentiment={sentiment} keywords={keywords}
          onAddAction={onAddAction} onToggleAction={onToggleAction} onDeleteAction={onDeleteAction}
        />
      )}
    </div>
  );
}

const s = {
  panel: { background: 'var(--surface)', border: '1px solid var(--border)', borderRadius: 'var(--r-xl)', display: 'flex', flexDirection: 'column', overflow: 'hidden', boxShadow: 'var(--shadow-md)', minHeight: 0 },
  tabs: { display: 'flex', borderBottom: '1px solid var(--border)', flexShrink: 0 },
  tab: { flex: 1, padding: '14px 10px', background: 'transparent', border: 'none', cursor: 'pointer', fontFamily: 'var(--font-body)', fontSize: 12, fontWeight: 600, color: 'var(--text-3)', transition: 'all 0.2s' },
  tabActive: { color: 'var(--brand-light)', borderBottom: '2px solid var(--brand)', background: 'var(--brand-muted)' },
  // Chat
  chatBody: { flex: 1, overflowY: 'auto', padding: '16px 18px', minHeight: 0, display: 'flex', flexDirection: 'column', gap: 12 },
  bubbleWrap: { display: 'flex' },
  bubble: { maxWidth: '88%', padding: '10px 14px', borderRadius: 'var(--r-md)', lineHeight: 1.6, wordBreak: 'break-word' },
  bubbleUser: { background: 'var(--brand)', color: '#fff', fontSize: 13.5, borderTopRightRadius: 4 },
  bubbleAssistant: { background: 'var(--surface-2)', color: 'var(--text-1)', fontSize: 13.5, border: '1px solid var(--border)', borderTopLeftRadius: 4 },
  inputArea: { borderTop: '1px solid var(--border)', padding: '12px 16px', display: 'flex', gap: 8, alignItems: 'flex-end', flexShrink: 0 },
  textarea: { flex: 1, background: 'var(--surface-3)', border: '1px solid var(--border-bright)', borderRadius: 'var(--r-pill)', padding: '9px 16px', fontFamily: 'var(--font-body)', fontSize: 13.5, color: 'var(--text-1)', resize: 'none', outline: 'none', minHeight: 40, maxHeight: 120, lineHeight: 1.5 },
  sendBtn: { background: 'var(--brand)', border: 'none', borderRadius: '50%', width: 40, height: 40, flexShrink: 0, cursor: 'pointer', display: 'flex', alignItems: 'center', justifyContent: 'center', transition: 'all 0.2s' },
  // Board
  board: { flex: 1, overflowY: 'auto', padding: 18, display: 'flex', flexDirection: 'column', gap: 20 },
  section: { display: 'flex', flexDirection: 'column', gap: 10 },
  sectionTitle: { fontSize: 10, fontWeight: 700, letterSpacing: '0.09em', textTransform: 'uppercase', color: 'var(--text-3)' },
  sentimentBadge: { display: 'flex', alignItems: 'center', gap: 10, padding: '10px 16px', borderRadius: 'var(--r-md)' },
  tagCloud: { display: 'flex', flexWrap: 'wrap', gap: 6 },
  keyword: { fontSize: 11, fontWeight: 600, color: 'var(--brand-light)', background: 'var(--brand-muted)', padding: '4px 10px', borderRadius: 'var(--r-pill)' },
  decisionItem: { display: 'flex', gap: 10, alignItems: 'flex-start', padding: '8px 12px', background: 'rgba(16,185,129,0.07)', borderRadius: 'var(--r-md)', border: '1px solid rgba(16,185,129,0.15)' },
  decisionDot: { color: '#10B981', fontWeight: 700, flexShrink: 0, fontSize: 13, marginTop: 1 },
  emptyNote: { fontSize: 12, color: 'var(--text-3)', fontStyle: 'italic' },
  actionItem: { display: 'flex', alignItems: 'flex-start', gap: 10, padding: '10px 12px', background: 'var(--surface-2)', border: '1px solid var(--border)', borderRadius: 'var(--r-md)', transition: 'opacity 0.2s' },
  checkBtn: { width: 22, height: 22, border: '1.5px solid var(--border-bright)', borderRadius: 6, background: 'transparent', cursor: 'pointer', display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0, color: '#10B981' },
  emptyCheck: { display: 'block', width: 10, height: 10 },
  deleteBtn: { width: 24, height: 24, border: 'none', background: 'transparent', cursor: 'pointer', color: 'var(--text-3)', display: 'flex', alignItems: 'center', justifyContent: 'center', borderRadius: 4, flexShrink: 0 },
  addTaskRow: { display: 'flex', gap: 8, marginTop: 4 },
  addInput: { flex: 1, background: 'var(--surface-3)', border: '1px solid var(--border-bright)', borderRadius: 'var(--r-md)', padding: '8px 12px', fontSize: 13, color: 'var(--text-1)', outline: 'none', fontFamily: 'var(--font-body)' },
  addBtn: { width: 34, height: 34, background: 'var(--brand-muted)', border: '1px solid var(--brand)', borderRadius: 'var(--r-md)', cursor: 'pointer', display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'var(--brand-light)', flexShrink: 0 },
};
