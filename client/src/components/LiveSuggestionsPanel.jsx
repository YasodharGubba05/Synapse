import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import SuggestionCard from './SuggestionCard';
import { fetchSuggestions } from '../api';
import { AVAILABLE_PLAYBOOKS } from '../sessionSettings';

const RefreshIcon = () => (
  <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
    <polyline points="1 4 1 10 7 10"/><path d="M3.51 15a9 9 0 1 0 .49-3.45"/>
  </svg>
);

const KeyIcon = () => (
  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
    <circle cx="7.5" cy="15.5" r="4.5"/><path d="M10.7 12.3 21 2"/><path d="m16.5 6.5 3 3"/>
  </svg>
);
const SparkIcon = () => (
  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
    <path d="M12 3v4M12 17v4M3 12h4M17 12h4M5.6 5.6l2.8 2.8M15.6 15.6l2.8 2.8M18.4 5.6l-2.8 2.8M8.4 15.6l-2.8 2.8"/>
  </svg>
);

export default function LiveSuggestionsPanel({
  transcriptText, spokenTranscriptText, hasApiKey, isRecording,
  batches, settings, latestTranscriptChunk, onBatchCreated,
  onManualRefresh, onSuggestionClick, refreshRequest, silenceStreakCount,
}) {
  const [error, setError] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const lastAutoChunkRef = useRef('');
  const lastRefreshTokenRef = useRef(0);
  const inFlightKeyRef = useRef('');
  const lastCompletedKeyRef = useRef('');

  const transcriptWordCount = useMemo(
    () => spokenTranscriptText.trim().split(/\s+/).filter(Boolean).length,
    [spokenTranscriptText]
  );

  const previousSuggestions = useMemo(
    () => batches.slice(0, 3).flatMap(b => b.suggestions.map(s => `${s.type}: ${s.title} - ${s.preview}`)).slice(0, 9),
    [batches]
  );

  const pullSuggestions = useCallback(async (source = 'auto') => {
    if (!hasApiKey || !transcriptText.trim()) return;
    const requestKey = source === 'auto' ? `auto:${latestTranscriptChunk}` : `${source}:${refreshRequest?.token || silenceStreakCount}:${batches.length}`;
    if (!latestTranscriptChunk.trim() && source === 'auto') return;
    if (inFlightKeyRef.current === requestKey || lastCompletedKeyRef.current === requestKey) return;

    try {
      inFlightKeyRef.current = requestKey;
      setIsLoading(true);
      setError('');
      const data = await fetchSuggestions({
        transcript_slice: transcriptText,
        latest_transcript_chunk: latestTranscriptChunk,
        meeting_memory: settings.meetingMemory,
        previous_suggestions: previousSuggestions,
        silence_streak_count: silenceStreakCount,
        context_window: settings.suggestionsContextWindow,
        suggestions_prompt: settings.suggestionsPrompt || undefined,
        session_id: settings.sessionId,
        model: settings.selectedModel,
        playbook: settings.playbook,
      });
      const items = Array.isArray(data?.suggestions) ? data.suggestions : [];
      if (items.length === 3) onBatchCreated?.(items, source);
      lastCompletedKeyRef.current = requestKey;
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unable to load suggestions.');
    } finally {
      if (inFlightKeyRef.current === requestKey) inFlightKeyRef.current = '';
      setIsLoading(false);
    }
  }, [hasApiKey, batches.length, latestTranscriptChunk, onBatchCreated, previousSuggestions, refreshRequest, settings, silenceStreakCount, transcriptText]);

  useEffect(() => {
    if (!refreshRequest?.token || !hasApiKey || !transcriptText.trim()) return;
    if (refreshRequest.source === 'auto') {
      if (!isRecording || transcriptWordCount < 8 || !latestTranscriptChunk.trim()) return;
      if (lastAutoChunkRef.current === latestTranscriptChunk) return;
      lastAutoChunkRef.current = latestTranscriptChunk;
    }
    if (lastRefreshTokenRef.current === refreshRequest.token) return;
    lastRefreshTokenRef.current = refreshRequest.token;
    const timer = setTimeout(() => pullSuggestions(refreshRequest.source || 'manual'), 0);
    return () => clearTimeout(timer);
  }, [hasApiKey, isRecording, latestTranscriptChunk, pullSuggestions, refreshRequest, transcriptText, transcriptWordCount]);

  const activePlaybook = AVAILABLE_PLAYBOOKS.find(p => p.value === settings.playbook) || AVAILABLE_PLAYBOOKS[0];

  return (
    <div style={s.panel}>
      <div style={s.header}>
        <div style={s.headerTop}>
          <span className="panel-label">Live Suggestions</span>
          <div style={s.headerControls}>
            <span style={s.playbookBadge}>{activePlaybook.icon} {activePlaybook.label}</span>
            <button
              className="btn-quiet"
              onClick={onManualRefresh}
              disabled={!hasApiKey || !transcriptText.trim() || isLoading}
              title="Generate a fresh set of suggestions"
            >
              <RefreshIcon />
              {isLoading ? 'Generating…' : 'Refresh'}
            </button>
          </div>
        </div>
        {isLoading && (
          <div style={s.loadingRow}>
            <div style={{ ...s.shimmer, width: '60%' }} className="shimmer-loading" />
            <div style={{ ...s.shimmer, width: '80%' }} className="shimmer-loading" />
            <div style={{ ...s.shimmer, width: '50%' }} className="shimmer-loading" />
          </div>
        )}
      </div>

      <div style={s.body} className="scrollable">
        {error && <div style={s.error}>{error}</div>}
        {!hasApiKey && (
          <div className="empty-state">
            <span className="empty-mark"><KeyIcon /></span>
            <span className="empty-title">No API key yet</span>
            <span className="empty-hint">Add your Groq key under Settings to turn on transcription and live suggestions.</span>
          </div>
        )}
        {hasApiKey && !isRecording && batches.length === 0 && (
          <div className="empty-state">
            <span className="empty-mark"><SparkIcon /></span>
            <span className="empty-title">Nothing to suggest yet</span>
            <span className="empty-hint">Start recording and suggestions will appear here as the conversation develops.</span>
          </div>
        )}
        {hasApiKey && isRecording && transcriptWordCount < 8 && (
          <div className="empty-state">
            <span className="empty-title">Listening…</span>
            <span className="empty-hint">Suggestions appear once there are a few sentences to work with.</span>
          </div>
        )}
        {silenceStreakCount > 0 && (
          <div style={s.silenceBadge}>
            🔇 Silent for {silenceStreakCount * 30}s — ideas for restarting will surface shortly
          </div>
        )}

        {batches.map((batch, batchIdx) => (
          <React.Fragment key={batch.id}>
            {batchIdx === 0 && (
              <div style={s.batchLabel}>
                Latest · {batch.time}
                {batch.source !== 'auto' && <span style={s.sourceTag}>{batch.source}</span>}
              </div>
            )}
            {batch.suggestions.map((sug, i) => (
              <SuggestionCard
                key={`${batch.id}-${i}`}
                type={sug.type} title={sug.title} preview={sug.preview}
                faded={batchIdx > 0}
                onClick={onSuggestionClick}
              />
            ))}
            {batchIdx === 0 && batches.length > 1 && <div style={s.divider} />}
          </React.Fragment>
        ))}
      </div>
    </div>
  );
}

const s = {
  panel: { background: 'var(--fill-panel)', border: '1px solid var(--border)', borderRadius: 'var(--r-xl)', display: 'flex', flexDirection: 'column', overflow: 'hidden', boxShadow: 'var(--highlight), var(--shadow-md)', minHeight: 0 },
  header: { padding: '14px 16px', borderBottom: '1px solid var(--border)', flexShrink: 0 },
  headerTop: { display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 10 },
  headerControls: { display: 'flex', alignItems: 'center', gap: 8 },
  label: { fontFamily: 'var(--font-head)', fontSize: 11, fontWeight: 700, letterSpacing: '0.08em', textTransform: 'uppercase', color: 'var(--text-3)' },
  playbookBadge: { fontSize: 'var(--fs-meta)', fontWeight: 500, color: 'var(--text-2)', background: 'var(--surface-2)', border: '1px solid var(--border)', padding: '3px 8px', borderRadius: 'var(--r-sm)', whiteSpace: 'nowrap' },
  loadingRow: { display: 'flex', flexDirection: 'column', gap: 6, marginTop: 12 },
  shimmer: { height: 12 },
  body: { flex: 1, overflowY: 'auto', padding: 16, display: 'flex', flexDirection: 'column', gap: 10, minHeight: 0 },
  silenceBadge: { fontSize: 'var(--fs-sm)', color: 'var(--accent-amber)', background: 'rgba(251,191,36,0.08)', border: '1px solid rgba(251,191,36,0.18)', borderRadius: 'var(--r-md)', padding: '9px 12px', lineHeight: 1.5 },
  error: { fontSize: 'var(--fs-sm)', color: 'var(--accent-rose)', background: 'rgba(251,113,133,0.08)', border: '1px solid rgba(251,113,133,0.18)', borderRadius: 'var(--r-md)', padding: '9px 12px', lineHeight: 1.5 },
  batchLabel: { fontSize: 'var(--fs-micro)', fontWeight: 600, letterSpacing: '0.08em', textTransform: 'uppercase', color: 'var(--text-3)', display: 'flex', alignItems: 'center', gap: 8, marginTop: 2 },
  sourceTag: { padding: '1px 6px', background: 'var(--surface-3)', color: 'var(--text-2)', borderRadius: 'var(--r-sm)', fontSize: 9, letterSpacing: '0.04em' },
  divider: { height: 1, background: 'var(--border)', margin: '4px 0' },
};
