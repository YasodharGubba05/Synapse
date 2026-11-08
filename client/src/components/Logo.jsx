import React from 'react';

/**
 * The Synapse mark.
 *
 * A synapse is the junction where a signal jumps the gap between two neurons,
 * so the mark is exactly that: a solid presynaptic terminal, two signal dots
 * crossing the cleft, and an open postsynaptic receptor. The diagonal reads
 * as transmission and direction, and the whole thing holds together down to
 * 16px because it is only four shapes.
 *
 * Draws in `currentColor`, so it inherits whatever the surface sets.
 */
export function SynapseMark({ size = 18, strokeWidth = 2.05 }) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      aria-hidden="true"
      focusable="false"
    >
      {/* Presynaptic terminal — the signal starts here */}
      <circle cx="6.6" cy="17.4" r="3.1" fill="currentColor" />
      {/* Crossing the cleft */}
      <circle cx="10.6" cy="13.4" r="1.25" fill="currentColor" />
      <circle cx="13.4" cy="10.6" r="1.2" fill="currentColor" opacity="0.72" />
      {/* Postsynaptic receptor — open, waiting to receive */}
      <circle cx="17.4" cy="6.6" r="3.1" stroke="currentColor" strokeWidth={strokeWidth} />
    </svg>
  );
}

/** The mark on its brand chip, as it appears in the navbar and auth screen. */
export function LogoChip({ size = 30, markSize = 18 }) {
  return (
    <div style={{ ...chip, width: size, height: size }}>
      <SynapseMark size={markSize} />
    </div>
  );
}

const chip = {
  background: 'linear-gradient(180deg, var(--brand) 0%, var(--brand-deep) 100%)',
  border: '1px solid rgba(255,255,255,0.16)',
  boxShadow: 'var(--highlight-strong), 0 2px 8px -2px rgba(92,108,232,0.5)',
  borderRadius: 'var(--r-md)',
  display: 'flex',
  alignItems: 'center',
  justifyContent: 'center',
  color: '#fff',
  flexShrink: 0,
};

/** Product tagline, shown under the wordmark. */
export const BRAND_TAGLINE = 'Real-time meeting copilot';
