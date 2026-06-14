import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import SuggestionCard from './SuggestionCard';
import { fetchSuggestions } from '../api';
import { AVAILABLE_PLAYBOOKS } from '../sessionSettings';

const RefreshIcon = () => (
  <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
    <polyline points="1 4 1 10 7 10"/><path d="M3.51 15a9 9 0 1 0 .49-3.45"/>
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
          <span style={s.label}>Live Suggestions</span>
          <span style={s.playbookBadge}>{activePlaybook.icon} {activePlaybook.label}</span>
        </div>
        <div style={s.headerBottom}>
          <button
            className="btn-primary"
            style={{ fontSize: 12, padding: '6px 14px', gap: 6 }}
            onClick={onManualRefresh}
            disabled={!hasApiKey || !transcriptText.trim() || isLoading}
          >
            <RefreshIcon />
            {isLoading ? 'Generating...' : 'Refresh Now'}
          </button>
          {isLoading && (
            <div style={s.loadingRow}>
              <div style={{ ...s.shimmer, width: '60%' }} className="shimmer-loading" />
              <div style={{ ...s.shimmer, width: '80%' }} className="shimmer-loading" />
              <div style={{ ...s.shimmer, width: '50%' }} className="shimmer-loading" />
            </div>
          )}
        </div>
      </div>

      <div style={s.body} className="scrollable">
        {error && <div style={s.error}>{error}</div>}
        {!hasApiKey && <div style={s.placeholder}>Add a Groq API key in Settings to get started.</div>}
        {hasApiKey && !isRecording && batches.length === 0 && (
          <div style={s.placeholder}>Start recording to generate live AI suggestions.</div>
        )}
        {hasApiKey && isRecording && transcriptWordCount < 8 && (
          <div style={s.placeholder}>Keep talking... suggestions appear after a few sentences.</div>
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
  panel: { background: 'var(--surface)', border: '1px solid var(--border)', borderRadius: 'var(--r-xl)', display: 'flex', flexDirection: 'column', overflow: 'hidden', boxShadow: 'var(--shadow-md)', minHeight: 0 },
  header: { padding: '16px 18px', borderBottom: '1px solid var(--border)', flexShrink: 0 },
  headerTop: { display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 10 },
  label: { fontFamily: 'var(--font-head)', fontSize: 11, fontWeight: 700, letterSpacing: '0.08em', textTransform: 'uppercase', color: 'var(--text-3)' },
  playbookBadge: { fontSize: 11, fontWeight: 600, color: 'var(--brand-light)', background: 'var(--brand-muted)', padding: '3px 10px', borderRadius: 'var(--r-pill)' },
  headerBottom: { display: 'flex', flexDirection: 'column', gap: 8 },
  loadingRow: { display: 'flex', flexDirection: 'column', gap: 6, marginTop: 4 },
  shimmer: { height: 12 },
  body: { flex: 1, overflowY: 'auto', padding: 16, display: 'flex', flexDirection: 'column', gap: 10, minHeight: 0 },
  placeholder: { fontSize: 13, color: 'var(--text-3)', border: '1px dashed var(--border-bright)', borderRadius: 'var(--r-md)', padding: 14, textAlign: 'center' },
  silenceBadge: { fontSize: 12, color: 'var(--accent-amber)', background: 'rgba(245,158,11,0.1)', border: '1px solid rgba(245,158,11,0.2)', borderRadius: 'var(--r-md)', padding: '10px 14px' },
  error: { fontSize: 12, color: '#FB7185', background: 'rgba(244,63,94,0.1)', border: '1px solid rgba(244,63,94,0.2)', borderRadius: 'var(--r-md)', padding: 10 },
  batchLabel: { fontSize: 10, fontWeight: 700, letterSpacing: '0.07em', textTransform: 'uppercase', color: 'var(--text-3)', display: 'flex', alignItems: 'center', gap: 8 },
  sourceTag: { padding: '1px 7px', background: 'var(--brand-muted)', color: 'var(--brand-light)', borderRadius: 'var(--r-pill)', fontSize: 9 },
  divider: { height: 1, background: 'var(--border)', margin: '4px 0' },
};
