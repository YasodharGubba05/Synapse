import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import './styles.css';

import Navbar from './components/Navbar';
import TranscriptPanel from './components/TranscriptPanel';
import LiveSuggestionsPanel from './components/LiveSuggestionsPanel';
import WorkspacePanel from './components/WorkspacePanel';
import HistorySidebar from './components/HistorySidebar';
import {
  exportSessionAsJson, fetchIntelligence, startMeeting, endMeeting, warmupBackend,
  patchActionItemStatus, deleteActionItemApi,
} from './api';
import { formatSessionTimestamp, loadSessionSettings, saveSessionSettings } from './sessionSettings';

let _actionIdCounter = 1;

export default function App() {
  const transcriptPanelRef = useRef(null);
  const nextSuggestionBatchIdRef = useRef(1);
  const startupWarmupSentRef = useRef(false);
  const lastApiKeyRef = useRef('');
  const intelligenceTimerRef = useRef(null);

  const [settings, setSettings] = useState(loadSessionSettings);
  const [pendingMessage, setPendingMessage] = useState(null);
  const [transcriptEntries, setTranscriptEntries] = useState([]);
  const [suggestionBatches, setSuggestionBatches] = useState([]);
  const [chatMessages, setChatMessages] = useState([]);
  const [isRecording, setIsRecording] = useState(false);
  const [latestTranscriptChunk, setLatestTranscriptChunk] = useState('');
  const [silenceStreakCount, setSilenceStreakCount] = useState(0);
  const [refreshRequest, setRefreshRequest] = useState({ token: 0, source: 'manual' });
  const [sessionId, setSessionId] = useState(null);
  const [historyOpen, setHistoryOpen] = useState(false);
  // Workspace board state
  const [actionItems, setActionItems] = useState([]);
  const [decisions, setDecisions] = useState([]);
  const [sentiment, setSentiment] = useState('neutral');
  const [keywords, setKeywords] = useState([]);

  const hasApiKey = settings.apiKey.trim().length > 0;

  // Apply theme to document
  useEffect(() => {
    document.documentElement.setAttribute('data-theme', settings.theme || 'dark');
  }, [settings.theme]);

  // Warmup backend on api key change
  useEffect(() => {
    const key = settings.apiKey.trim();
    if (key !== lastApiKeyRef.current) {
      startupWarmupSentRef.current = false;
      lastApiKeyRef.current = key;
    }
  }, [settings.apiKey]);

  useEffect(() => {
    if (!hasApiKey || startupWarmupSentRef.current) return;
    startupWarmupSentRef.current = true;
    warmupBackend().catch(() => { startupWarmupSentRef.current = false; });
  }, [hasApiKey]);

  const handleSaveSettings = useCallback((next) => {
    const normalized = saveSessionSettings(next);
    setSettings(normalized);
  }, []);

  // Start/stop DB sessions with recording
  const handleRecordingChange = useCallback(async (recording) => {
    setIsRecording(recording);
    if (recording && hasApiKey) {
      try {
        const data = await startMeeting({
          meeting_memory: settings.meetingMemory,
          playbook: settings.playbook,
          title: `Meeting ${new Date().toLocaleDateString()} ${new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}`,
        });
        setSessionId(data.session_id);
        handleSaveSettings({ ...settings, sessionId: data.session_id });
      } catch { /* non-fatal */ }
    } else if (!recording && sessionId && hasApiKey) {
      endMeeting({ session_id: sessionId }).catch(() => {});
    }
  }, [hasApiKey, sessionId, settings, handleSaveSettings]);

  const handleTranscriptChunk = useCallback((text) => {
    const trimmed = text.trim();
    if (!trimmed) return;
    const ts = formatSessionTimestamp();
    setLatestTranscriptChunk(trimmed);
    setSilenceStreakCount(0);
    setTranscriptEntries(prev => [...prev, { time: ts.label, isoTime: ts.iso, text: trimmed, kind: 'speech' }]);
    setRefreshRequest({ token: Date.now(), source: 'auto' });
  }, []);

  const handleSilencePeriod = useCallback(({ streakCount, secondsSilent }) => {
    const ts = formatSessionTimestamp();
    const silenceText = streakCount === 1 ? `[Silence for ${secondsSilent}s]` : `[Silence continuing for ${secondsSilent}s total]`;
    setSilenceStreakCount(streakCount);
    setTranscriptEntries(prev => {
      const next = [...prev];
      const last = next[next.length - 1];
      if (last?.kind === 'silence') {
        next[next.length - 1] = { ...last, time: ts.label, isoTime: ts.iso, text: silenceText, silenceSeconds: secondsSilent };
        return next;
      }
      return [...next, { time: ts.label, isoTime: ts.iso, text: silenceText, kind: 'silence', silenceSeconds: secondsSilent }];
    });
    const hasContext = latestTranscriptChunk.trim().length > 0 || transcriptEntries.some(e => e.kind === 'speech');
    if (hasContext && (streakCount === 1 || streakCount % 3 === 0)) {
      setRefreshRequest({ token: Date.now(), source: 'silence' });
    }
  }, [latestTranscriptChunk, transcriptEntries]);

  // Intelligence polling
  const runIntelligence = useCallback(async (transcript) => {
    if (!hasApiKey || !transcript.trim() || transcript.trim().split(/\s+/).length < 20) return;
    try {
      const data = await fetchIntelligence({
        transcript_slice: transcript,
        playbook: settings.playbook,
        context_window: 1000,
        session_id: sessionId || undefined,
        model: settings.selectedModel,
      });
      if (data.sentiment) setSentiment(data.sentiment);
      if (data.keywords?.length) setKeywords(data.keywords);
      if (data.decisions?.length) {
        setDecisions(prev => {
          const existing = new Set(prev.map(d => d.content));
          const newOnes = data.decisions.filter(d => !existing.has(d)).map(d => ({ id: `d-${Date.now()}-${Math.random()}`, content: d }));
          return [...prev, ...newOnes];
        });
      }
      if (data.action_items?.length) {
        setActionItems(prev => {
          const existing = new Set(prev.map(a => a.task));
          const newOnes = data.action_items.filter(a => !existing.has(a.task)).map(a => ({
            id: `local-${_actionIdCounter++}`, task: a.task, assignee: a.assignee, priority: a.priority, status: 'pending',
          }));
          return [...prev, ...newOnes];
        });
      }
    } catch { /* non-fatal */ }
  }, [hasApiKey, sessionId, settings.playbook, settings.selectedModel]);

  const fullTranscript = useMemo(() => transcriptEntries.map(e => e.text).join(' '), [transcriptEntries]);
  const spokenTranscript = useMemo(() => transcriptEntries.filter(e => e.kind !== 'silence').map(e => e.text).join(' '), [transcriptEntries]);

  // Throttled intelligence call every 2 new chunks
  const chunkCountRef = useRef(0);
  useEffect(() => {
    if (!latestTranscriptChunk) return;
    chunkCountRef.current += 1;
    if (chunkCountRef.current % 2 === 0) {
      clearTimeout(intelligenceTimerRef.current);
      intelligenceTimerRef.current = setTimeout(() => runIntelligence(fullTranscript), 500);
    }
  }, [latestTranscriptChunk, fullTranscript, runIntelligence]);

  const handleSuggestionBatch = useCallback((suggestions, source = 'auto') => {
    const ts = formatSessionTimestamp();
    setSuggestionBatches(prev => [{
      id: nextSuggestionBatchIdRef.current++,
      source, time: ts.label, isoTime: ts.iso, suggestions,
    }, ...prev]);
  }, []);

  const handleSuggestionClick = useCallback((text) => {
    setPendingMessage({ text, at: Date.now(), mode: 'suggestion' });
  }, []);

  const handleManualRefresh = useCallback(async () => {
    const hadNew = await transcriptPanelRef.current?.flushCurrentSegment?.();
    if (!hadNew) setRefreshRequest({ token: Date.now(), source: 'manual' });
  }, []);

  const handleExport = useCallback(() => {
    const exp = { ...settings }; delete exp.apiKey;
    exportSessionAsJson({ exported_at: new Date().toISOString(), transcript_entries: transcriptEntries, suggestion_batches: suggestionBatches, chat_history: chatMessages, action_items: actionItems, decisions, settings: exp });
  }, [chatMessages, settings, suggestionBatches, transcriptEntries, actionItems, decisions]);

  // Load session from history
  const handleLoadSession = useCallback((data) => {
    setTranscriptEntries(data.transcript_entries || []);
    setSuggestionBatches(
      (data.suggestions || []).length > 0
        ? [{ id: 1, source: 'history', time: '', isoTime: 'history', suggestions: data.suggestions }]
        : []
    );
    setChatMessages(data.chat_messages?.map((m, i) => ({ role: m.role, text: m.content, time: '', isoTime: `h-${i}` })) || []);
    setActionItems(data.action_items?.map(a => ({ ...a })) || []);
    setDecisions(data.decisions?.map(d => ({ ...d })) || []);
    setSessionId(data.id);
    handleSaveSettings({ ...settings, sessionId: data.id, playbook: data.playbook });
  }, [settings, handleSaveSettings]);

  // Action item handlers
  const handleAddAction = useCallback((task) => {
    setActionItems(prev => [...prev, { id: `local-${_actionIdCounter++}`, task, assignee: null, priority: 'medium', status: 'pending' }]);
  }, []);

  const handleToggleAction = useCallback(async (itemId, currentStatus) => {
    const next = currentStatus === 'completed' ? 'pending' : 'completed';
    setActionItems(prev => prev.map(a => a.id === itemId ? { ...a, status: next } : a));
    if (sessionId && !itemId.startsWith('local-')) {
      patchActionItemStatus(sessionId, itemId, next).catch(() => {});
    }
  }, [sessionId]);

  const handleDeleteAction = useCallback(async (itemId) => {
    setActionItems(prev => prev.filter(a => a.id !== itemId));
    if (sessionId && !itemId.startsWith('local-')) {
      deleteActionItemApi(sessionId, itemId).catch(() => {});
    }
  }, [sessionId]);

  const enrichedSettings = useMemo(() => ({ ...settings, sessionId }), [settings, sessionId]);
  const canExport = transcriptEntries.length > 0 || suggestionBatches.length > 0 || chatMessages.length > 0;

  return (
    <div style={{ height: '100vh', display: 'flex', flexDirection: 'column', background: 'var(--bg)', overflow: 'hidden' }}>
      <Navbar
        settings={settings}
        onSaveSettings={handleSaveSettings}
        onExportSession={handleExport}
        canExport={canExport}
        onToggleHistory={() => setHistoryOpen(true)}
      />

      <HistorySidebar open={historyOpen} onClose={() => setHistoryOpen(false)} onLoadSession={handleLoadSession} />

      <div className="app-layout" style={{
        flex: 1, display: 'grid', gridTemplateColumns: '30fr 38fr 32fr',
        gap: 12, padding: 12, overflow: 'hidden', minHeight: 0, height: '100%',
      }}>
        <TranscriptPanel
          ref={transcriptPanelRef}
          entries={transcriptEntries}
          hasApiKey={hasApiKey}
          onSilencePeriod={handleSilencePeriod}
          onTranscriptChunk={handleTranscriptChunk}
          onRecordingChange={handleRecordingChange}
        />

        <LiveSuggestionsPanel
          batches={suggestionBatches}
          hasApiKey={hasApiKey}
          isRecording={isRecording}
          latestTranscriptChunk={latestTranscriptChunk}
          onBatchCreated={handleSuggestionBatch}
          onManualRefresh={handleManualRefresh}
          onSuggestionClick={handleSuggestionClick}
          refreshRequest={refreshRequest}
          silenceStreakCount={silenceStreakCount}
          settings={enrichedSettings}
          transcriptText={fullTranscript}
          spokenTranscriptText={spokenTranscript}
        />

        <WorkspacePanel
          chatMessages={chatMessages}
          hasApiKey={hasApiKey}
          pendingMessage={pendingMessage}
          fullTranscript={fullTranscript}
          setChatMessages={setChatMessages}
          settings={enrichedSettings}
          actionItems={actionItems}
          decisions={decisions}
          sentiment={sentiment}
          keywords={keywords}
          onAddAction={handleAddAction}
          onToggleAction={handleToggleAction}
          onDeleteAction={handleDeleteAction}
        />
      </div>
    </div>
  );
}
