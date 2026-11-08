import React, { forwardRef, useEffect, useImperativeHandle, useRef, useState } from 'react';
import { transcribeAudioBlob } from '../api';

const MicIcon = () => (
  <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="white" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
    <rect x="9" y="2" width="6" height="11" rx="3"/>
    <path d="M5 10a7 7 0 0014 0M12 19v4M8 23h8"/>
  </svg>
);

const StopIcon = () => (
  <svg width="16" height="16" viewBox="0 0 24 24" fill="white" stroke="white" strokeWidth="1.5">
    <rect x="4" y="4" width="16" height="16" rx="2"/>
  </svg>
);

// Canvas audio visualizer
function AudioVisualizer({ stream, isRecording }) {
  const canvasRef = useRef(null);
  const animRef = useRef(null);
  const analyserRef = useRef(null);
  const sourceRef = useRef(null);
  const ctxRef = useRef(null);

  useEffect(() => {
    if (!isRecording || !stream) {
      if (animRef.current) cancelAnimationFrame(animRef.current);
      // Clear canvas
      const canvas = canvasRef.current;
      if (canvas) {
        const ctx = canvas.getContext('2d');
        ctx.clearRect(0, 0, canvas.width, canvas.height);
      }
      return;
    }

    const audioCtx = new (window.AudioContext || window.webkitAudioContext)();
    ctxRef.current = audioCtx;
    const analyser = audioCtx.createAnalyser();
    analyser.fftSize = 256;
    analyserRef.current = analyser;
    const source = audioCtx.createMediaStreamSource(stream);
    sourceRef.current = source;
    source.connect(analyser);

    const canvas = canvasRef.current;
    const ctx = canvas.getContext('2d');
    const bufferLength = analyser.frequencyBinCount;
    const dataArray = new Uint8Array(bufferLength);

    const draw = () => {
      animRef.current = requestAnimationFrame(draw);
      analyser.getByteFrequencyData(dataArray);

      const W = canvas.width;
      const H = canvas.height;
      ctx.clearRect(0, 0, W, H);

      const barWidth = (W / bufferLength) * 2.2;
      let x = 0;

      for (let i = 0; i < bufferLength; i++) {
        const barHeight = (dataArray[i] / 255) * H * 0.85;
        const hue = 260 + (dataArray[i] / 255) * 60; // purple → violet
        const alpha = 0.5 + (dataArray[i] / 255) * 0.5;
        ctx.fillStyle = `hsla(${hue}, 80%, 65%, ${alpha})`;
        ctx.beginPath();
        ctx.roundRect(x, H - barHeight, barWidth - 1, barHeight, 3);
        ctx.fill();
        x += barWidth + 1;
      }
    };
    draw();

    return () => {
      cancelAnimationFrame(animRef.current);
      source.disconnect();
      audioCtx.close();
    };
  }, [isRecording, stream]);

  return (
    <canvas
      ref={canvasRef}
      width={320}
      height={48}
      style={{ width: '100%', height: 48, borderRadius: 8, background: 'var(--surface-3)', display: 'block' }}
    />
  );
}

const TranscriptPanel = forwardRef(function TranscriptPanel(
  { entries, hasApiKey, onTranscriptChunk, onRecordingChange, onSilencePeriod },
  ref
) {
  const [isRecording, setIsRecording] = useState(false);
  const [statusText, setStatusText] = useState('Click to start recording');
  const [liveStream, setLiveStream] = useState(null);
  const bodyRef = useRef(null);
  const mediaRecorderRef = useRef(null);
  const streamRef = useRef(null);
  const segmentTimeoutRef = useRef(null);
  const isRecordingRef = useRef(false);
  const silenceStreakRef = useRef(0);
  const segmentChunksRef = useRef([]);
  const manualFlushResolveRef = useRef(null);

  const SEGMENT_DURATION_MS = 30000; // 30-second capture segments

  const getRecorderMimeType = () => {
    const candidates = [
      'audio/webm;codecs=opus',
      'audio/webm',
      'audio/mp4',
      'audio/ogg;codecs=opus',
      'audio/ogg',
    ];
    const supported = candidates.find(m => MediaRecorder.isTypeSupported(m));
    return supported || '';
  };

  const clearSegmentTimeout = () => {
    if (segmentTimeoutRef.current) { clearTimeout(segmentTimeoutRef.current); segmentTimeoutRef.current = null; }
  };

  const sendSegmentForTranscription = async (audioBlob) => {
    if (!audioBlob || audioBlob.size < 500) return false;
    try {
      setStatusText('Transcribing...');
      const result = await transcribeAudioBlob(audioBlob);
      const text = result?.text || '';
      if (text.trim()) {
        silenceStreakRef.current = 0;
        onTranscriptChunk(text);
        setStatusText('Recording live · capturing every 30s');
        return true;
      }
      silenceStreakRef.current += 1;
      onSilencePeriod?.({ streakCount: silenceStreakRef.current, secondsSilent: silenceStreakRef.current * SEGMENT_DURATION_MS / 1000 });
      setStatusText('No speech detected in last segment');
      return false;
    } catch (err) {
      console.error('[Synapse] Transcription error:', err);
      setStatusText(`Transcription error — ${err?.message || 'unknown'}`);
      return false;
    }
  };

  const startRecorderSegment = (stream) => {
    const mimeType = getRecorderMimeType();
    let recorder;
    try {
      recorder = mimeType ? new MediaRecorder(stream, { mimeType }) : new MediaRecorder(stream);
    } catch (e) {
      console.warn('[Synapse] Could not use mimeType', mimeType, '— falling back to default. Error:', e);
      recorder = new MediaRecorder(stream);
    }
    segmentChunksRef.current = [];

    // Collect ALL chunks in ondataavailable — called once on stop (no timeslice)
    recorder.ondataavailable = (e) => {
      if (e.data && e.data.size > 0) segmentChunksRef.current.push(e.data);
    };

    recorder.onstop = async () => {
      const effectiveMime = recorder.mimeType || mimeType || 'audio/webm';
      const blob = new Blob(segmentChunksRef.current, { type: effectiveMime });
      segmentChunksRef.current = [];
      const hadTranscript = await sendSegmentForTranscription(blob);
      if (manualFlushResolveRef.current) { manualFlushResolveRef.current(hadTranscript); manualFlushResolveRef.current = null; }
      if (isRecordingRef.current && streamRef.current) startRecorderSegment(streamRef.current);
    };

    recorder.onerror = (e) => {
      console.error('[Synapse] MediaRecorder error:', e);
      setStatusText('Recorder error — restarting...');
    };

    mediaRecorderRef.current = recorder;
    // Start WITHOUT timeslice — this ensures ondataavailable fires ONCE on stop
    // with a complete, valid audio container (not fragmented chunks).
    recorder.start();
    clearSegmentTimeout();
    segmentTimeoutRef.current = setTimeout(() => {
      if (recorder.state === 'recording') recorder.stop();
    }, SEGMENT_DURATION_MS);
  };

  useEffect(() => {
    if (bodyRef.current) bodyRef.current.scrollTop = bodyRef.current.scrollHeight;
  }, [entries]);

  useEffect(() => {
    return () => {
      isRecordingRef.current = false;
      clearSegmentTimeout();
      if (mediaRecorderRef.current?.state !== 'inactive') mediaRecorderRef.current?.stop();
      streamRef.current?.getTracks().forEach(t => t.stop());
    };
  }, []);

  useImperativeHandle(ref, () => ({
    async flushCurrentSegment() {
      if (!isRecordingRef.current || !mediaRecorderRef.current || mediaRecorderRef.current.state === 'inactive') return;
      clearSegmentTimeout();
      return new Promise((resolve) => {
        manualFlushResolveRef.current = resolve;
        mediaRecorderRef.current.stop();
      }).then((had) => { setStatusText('Segment flushed'); return had; });
    },
  }));

  const stopRecording = () => {
    isRecordingRef.current = false;
    clearSegmentTimeout();
    if (mediaRecorderRef.current?.state !== 'inactive') mediaRecorderRef.current?.stop();
    streamRef.current?.getTracks().forEach(t => t.stop());
    streamRef.current = null;
    setIsRecording(false);
    setLiveStream(null);
    silenceStreakRef.current = 0;
    onRecordingChange?.(false);
    setStatusText('Stopped · click to resume');
  };

  const startRecording = async () => {
    if (!hasApiKey) { setStatusText('Add API key in Settings first'); return; }
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      streamRef.current = stream;
      isRecordingRef.current = true;
      silenceStreakRef.current = 0;
      setIsRecording(true);
      setLiveStream(stream);
      onRecordingChange?.(true);
      setStatusText('Recording live · capturing every 30s');
      startRecorderSegment(stream);
    } catch {
      isRecordingRef.current = false;
      onRecordingChange?.(false);
      setStatusText('Microphone permission denied');
    }
  };

  return (
    <div style={s.panel}>
      <div style={s.header}>
        <div style={s.headerTop}>
          <span style={s.sectionLabel}>Transcript</span>
          <div style={s.statusBadge}>
            {isRecording ? <span className="live-dot" /> : <span style={s.idleDot} />}
            <span style={{ fontSize: 11, color: isRecording ? '#F87171' : 'var(--text-3)', fontWeight: 600 }}>
              {isRecording ? 'LIVE' : 'IDLE'}
            </span>
          </div>
        </div>

        {/* Audio Visualizer */}
        <AudioVisualizer stream={liveStream} isRecording={isRecording} />

        {/* Mic button + status */}
        <div style={s.micRow}>
          <div style={{ position: 'relative', display: 'inline-flex' }}>
            {isRecording && <div className="pulse-ring" />}
            <button
              style={{ ...s.micBtn, background: isRecording ? '#DC2626' : 'var(--brand)', boxShadow: isRecording ? '0 0 24px rgba(220,38,38,0.5)' : 'var(--shadow-brand)' }}
              onClick={isRecording ? stopRecording : startRecording}
              title={isRecording ? 'Stop recording' : 'Start recording'}
            >
              {isRecording ? <StopIcon /> : <MicIcon />}
            </button>
          </div>
          <span style={s.statusText}>{statusText}</span>
        </div>
      </div>

      <div ref={bodyRef} style={s.body} className="scrollable">
        {entries.length === 0 && (
          <div style={s.empty}>Transcript will appear here once recording starts.</div>
        )}
        {entries.map((entry, i) => (
          <div key={`${entry.isoTime}-${i}`} style={{ ...s.entry, borderBottom: i < entries.length - 1 ? '1px solid var(--border)' : 'none' }}>
            <div style={s.entryTime}>{entry.time}</div>
            <div style={{ ...s.entryText, opacity: entry.kind === 'silence' ? 0.45 : 1, fontStyle: entry.kind === 'silence' ? 'italic' : 'normal' }}>
              {entry.text}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
});

export default TranscriptPanel;

const s = {
  panel: { background: 'var(--surface)', border: '1px solid var(--border)', borderRadius: 'var(--r-xl)', display: 'flex', flexDirection: 'column', overflow: 'hidden', boxShadow: 'var(--shadow-md)', minHeight: 0 },
  header: { padding: '16px 18px', borderBottom: '1px solid var(--border)', display: 'flex', flexDirection: 'column', gap: 12, flexShrink: 0 },
  headerTop: { display: 'flex', alignItems: 'center', justifyContent: 'space-between' },
  sectionLabel: { fontFamily: 'var(--font-head)', fontSize: 11, fontWeight: 700, letterSpacing: '0.08em', textTransform: 'uppercase', color: 'var(--text-3)' },
  statusBadge: { display: 'flex', alignItems: 'center', gap: 5 },
  idleDot: { display: 'inline-block', width: 7, height: 7, background: 'var(--text-3)', borderRadius: '50%' },
  micRow: { display: 'flex', alignItems: 'center', gap: 12 },
  micBtn: { width: 42, height: 42, borderRadius: '50%', border: 'none', cursor: 'pointer', display: 'flex', alignItems: 'center', justifyContent: 'center', transition: 'all 0.3s', position: 'relative', zIndex: 2, flexShrink: 0 },
  statusText: { fontSize: 12, color: 'var(--text-2)', lineHeight: 1.4 },
  body: { flex: 1, overflowY: 'auto', padding: '4px 18px 18px', minHeight: 0 },
  empty: { marginTop: 20, fontSize: 13, color: 'var(--text-3)', textAlign: 'center' },
  entry: { padding: '12px 0' },
  entryTime: { fontSize: 10, fontWeight: 600, color: 'var(--text-3)', letterSpacing: '0.06em', marginBottom: 4 },
  entryText: { fontSize: 13.5, color: 'var(--text-1)', lineHeight: 1.65 },
};
