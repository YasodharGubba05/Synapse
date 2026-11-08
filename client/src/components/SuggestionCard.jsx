import React from 'react';

const TAG_CONFIG = {
  ANSWER:          { bg: 'var(--tag-answer)', color: 'var(--tag-answer-txt)', label: 'Answer' },
  QUESTION_TO_ASK: { bg: 'var(--tag-question)', color: 'var(--tag-question-txt)', label: 'Question to Ask' },
  TALKING_POINT:   { bg: 'var(--tag-talking)', color: 'var(--tag-talking-txt)', label: 'Talking Point' },
  FACT_CHECK:      { bg: 'var(--tag-fact)', color: 'var(--tag-fact-txt)', label: 'Fact Check' },
  CLARIFICATION:   { bg: 'var(--tag-clarify)', color: 'var(--tag-clarify-txt)', label: 'Clarification' },
};

export default function SuggestionCard({ type, title, preview, faded = false, onClick }) {
  const tag = TAG_CONFIG[type] ?? TAG_CONFIG.ANSWER;

  return (
    <div
      className="fade-in-up"
      style={{ ...s.card, opacity: faded ? 0.4 : 1 }}
      onClick={() => onClick?.(`${title}: ${preview}`)}
      onMouseEnter={e => {
        if (!faded) {
          e.currentTarget.style.borderColor = 'var(--border-bright)';
          e.currentTarget.style.background = 'var(--surface-3)';
        }
      }}
      onMouseLeave={e => {
        e.currentTarget.style.borderColor = 'var(--border)';
        e.currentTarget.style.background = 'var(--surface-2)';
      }}
    >
      <div style={{ ...s.tag, background: tag.bg, color: tag.color }}>
        <span style={{ width: 5, height: 5, borderRadius: '50%', background: tag.color, display: 'inline-block' }} />
        {tag.label}
      </div>
      <h4 style={s.title}>{title}</h4>
      <p style={s.preview}>{preview}</p>
      <div style={s.clickHint}>Click to expand →</div>
    </div>
  );
}

const s = {
  card: {
    background: 'var(--surface-2)',
    border: '1px solid var(--border)',
    borderRadius: 'var(--r-lg)',
    padding: '14px 16px',
    cursor: 'pointer',
    transition: 'background 0.15s ease, border-color 0.15s ease',
  },
  tag: {
    display: 'inline-flex', alignItems: 'center', gap: 5,
    fontSize: 'var(--fs-micro)', fontWeight: 600, letterSpacing: '0.07em', textTransform: 'uppercase',
    padding: '2px 7px', borderRadius: 'var(--r-sm)', marginBottom: 10,
  },
  title: { fontSize: 'var(--fs-body)', fontWeight: 600, color: 'var(--text-1)', lineHeight: 1.45, marginBottom: 5, letterSpacing: '-0.005em' },
  preview: { fontSize: 'var(--fs-sm)', color: 'var(--text-2)', lineHeight: 1.6 },
  clickHint: { fontSize: 'var(--fs-micro)', color: 'var(--text-3)', marginTop: 10, fontWeight: 500 },
};
