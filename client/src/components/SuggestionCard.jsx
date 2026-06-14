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
          e.currentTarget.style.borderColor = 'var(--brand)';
          e.currentTarget.style.transform = 'translateY(-2px)';
          e.currentTarget.style.boxShadow = '0 8px 30px rgba(124,58,237,0.2)';
        }
      }}
      onMouseLeave={e => {
        e.currentTarget.style.borderColor = 'var(--border)';
        e.currentTarget.style.transform = 'none';
        e.currentTarget.style.boxShadow = 'none';
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
    padding: '16px 18px',
    cursor: 'pointer',
    transition: 'all 0.2s ease',
  },
  tag: {
    display: 'inline-flex', alignItems: 'center', gap: 5,
    fontSize: 10, fontWeight: 700, letterSpacing: '0.07em', textTransform: 'uppercase',
    padding: '3px 9px', borderRadius: 'var(--r-pill)', marginBottom: 10,
  },
  title: { fontSize: 13.5, fontWeight: 600, color: 'var(--text-1)', lineHeight: 1.4, marginBottom: 6 },
  preview: { fontSize: 12.5, color: 'var(--text-2)', lineHeight: 1.6 },
  clickHint: { fontSize: 10, color: 'var(--text-3)', marginTop: 10, fontWeight: 500 },
};
