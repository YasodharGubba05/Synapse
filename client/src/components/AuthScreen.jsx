import React, { useMemo, useState } from 'react';
import { useAuth } from '../authContext';

const MIN_PASSWORD_LENGTH = 10;

const SpinnerIcon = () => (
  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round">
    <path d="M12 2a10 10 0 0 1 10 10">
      <animateTransform attributeName="transform" type="rotate" from="0 12 12" to="360 12 12" dur="0.8s" repeatCount="indefinite" />
    </path>
  </svg>
);

/** Mirrors the server-side policy so problems surface before a round trip. */
function localPasswordProblem(password) {
  if (password.length < MIN_PASSWORD_LENGTH) {
    return `Use at least ${MIN_PASSWORD_LENGTH} characters`;
  }
  if (!/[a-zA-Z]/.test(password)) return 'Include at least one letter';
  if (!/[0-9]/.test(password)) return 'Include at least one number';
  if (password.trim() !== password) return 'Remove the leading or trailing space';
  return '';
}

export default function AuthScreen() {
  const { login, register } = useAuth();
  const [mode, setMode] = useState('login');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [fullName, setFullName] = useState('');
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);

  const isRegister = mode === 'register';
  const passwordHint = useMemo(
    () => (isRegister && password ? localPasswordProblem(password) : ''),
    [isRegister, password],
  );

  const switchMode = (next) => {
    setMode(next);
    setError('');
    setPassword('');
    setConfirmPassword('');
  };

  const canSubmit =
    email.trim().length > 3 &&
    password.length > 0 &&
    !busy &&
    (!isRegister || (!passwordHint && password === confirmPassword));

  const handleSubmit = async (event) => {
    event.preventDefault();
    if (!canSubmit) return;
    setError('');
    setBusy(true);
    try {
      if (isRegister) {
        await register({ email: email.trim(), password, fullName: fullName.trim() || undefined });
      } else {
        await login({ email: email.trim(), password });
      }
    } catch (err) {
      setError(err?.message || 'Something went wrong. Please try again.');
      setPassword('');
      setConfirmPassword('');
    } finally {
      setBusy(false);
    }
  };

  return (
    <div style={s.page}>
      <div style={s.glow} aria-hidden="true" />

      <form style={s.card} onSubmit={handleSubmit} className="fade-in-up">
        <div style={s.brand}>
          <div style={s.brandLogo}><span style={s.brandIcon}>⚡</span></div>
          <div>
            <span style={s.brandName}>Synapse</span>
            <span style={s.brandTag}>Live Intelligence</span>
          </div>
        </div>

        <h1 style={s.heading}>
          {isRegister ? 'Create your account' : 'Welcome back'}
        </h1>
        <p style={s.subheading}>
          {isRegister
            ? 'Your meetings, transcripts and action items stay private to your account.'
            : 'Sign in to open your Synapse workspace.'}
        </p>

        <div style={s.tabs} role="tablist">
          <button
            type="button"
            role="tab"
            aria-selected={!isRegister}
            style={{ ...s.tab, ...(!isRegister ? s.tabActive : {}) }}
            onClick={() => switchMode('login')}
          >
            Sign in
          </button>
          <button
            type="button"
            role="tab"
            aria-selected={isRegister}
            style={{ ...s.tab, ...(isRegister ? s.tabActive : {}) }}
            onClick={() => switchMode('register')}
          >
            Create account
          </button>
        </div>

        {isRegister && (
          <div style={s.fieldGroup}>
            <label style={s.label} htmlFor="auth-name">Full name <span style={s.optional}>optional</span></label>
            <input
              id="auth-name"
              style={s.input}
              type="text"
              autoComplete="name"
              value={fullName}
              onChange={e => setFullName(e.target.value)}
              placeholder="Ada Lovelace"
            />
          </div>
        )}

        <div style={s.fieldGroup}>
          <label style={s.label} htmlFor="auth-email">Email</label>
          <input
            id="auth-email"
            style={s.input}
            type="email"
            required
            autoComplete="email"
            autoFocus
            value={email}
            onChange={e => setEmail(e.target.value)}
            placeholder="you@company.com"
          />
        </div>

        <div style={s.fieldGroup}>
          <label style={s.label} htmlFor="auth-password">Password</label>
          <input
            id="auth-password"
            style={s.input}
            type="password"
            required
            autoComplete={isRegister ? 'new-password' : 'current-password'}
            value={password}
            onChange={e => setPassword(e.target.value)}
            placeholder={isRegister ? `At least ${MIN_PASSWORD_LENGTH} characters` : '••••••••••'}
          />
          {isRegister && (
            <span style={{ ...s.helper, color: passwordHint ? 'var(--accent-amber)' : 'var(--text-3)' }}>
              {passwordHint || `${MIN_PASSWORD_LENGTH}+ characters, with a letter and a number`}
            </span>
          )}
        </div>

        {isRegister && (
          <div style={s.fieldGroup}>
            <label style={s.label} htmlFor="auth-confirm">Confirm password</label>
            <input
              id="auth-confirm"
              style={s.input}
              type="password"
              required
              autoComplete="new-password"
              value={confirmPassword}
              onChange={e => setConfirmPassword(e.target.value)}
              placeholder="Repeat your password"
            />
            {confirmPassword && confirmPassword !== password && (
              <span style={{ ...s.helper, color: 'var(--accent-amber)' }}>Passwords do not match</span>
            )}
          </div>
        )}

        {error && <div style={s.error} role="alert">{error}</div>}

        <button type="submit" style={{ ...s.submit, ...(canSubmit ? {} : s.submitDisabled) }} disabled={!canSubmit}>
          {busy && <SpinnerIcon />}
          {busy
            ? (isRegister ? 'Creating account…' : 'Signing in…')
            : (isRegister ? 'Create account' : 'Sign in')}
        </button>

        <p style={s.footnote}>
          Your Groq API key is never part of your account. You will add it in
          Settings after signing in, and it stays in this browser tab only.
        </p>
      </form>
    </div>
  );
}

const s = {
  page: {
    position: 'relative',
    minHeight: '100vh',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    background: 'var(--bg)',
    padding: 24,
    overflowY: 'auto',
  },
  glow: {
    position: 'absolute',
    inset: 0,
    background: 'radial-gradient(ellipse 80% 50% at 50% -10%, rgba(125,138,244,0.07), transparent 70%)',
    pointerEvents: 'none',
  },
  card: {
    position: 'relative',
    width: 'min(440px, 100%)',
    background: 'var(--surface)',
    border: '1px solid var(--border)',
    borderRadius: 'var(--r-xl)',
    boxShadow: 'var(--shadow-lg)',
    padding: 30,
    display: 'flex',
    flexDirection: 'column',
  },
  brand: { display: 'flex', alignItems: 'center', gap: 10, marginBottom: 22 },
  brandLogo: {
    width: 30, height: 30,
    background: 'var(--surface-3)',
    border: '1px solid var(--border-bright)',
    borderRadius: 'var(--r-md)',
    display: 'flex', alignItems: 'center', justifyContent: 'center',
  },
  brandIcon: { fontSize: 15 },
  brandName: { display: 'block', fontFamily: 'var(--font-head)', fontSize: 15, fontWeight: 700, letterSpacing: '-0.01em', color: 'var(--text-1)', lineHeight: 1.15 },
  brandTag: { display: 'block', fontSize: 9, fontWeight: 600, letterSpacing: '0.1em', textTransform: 'uppercase', color: 'var(--text-3)', marginTop: 1 },
  heading: { fontFamily: 'var(--font-head)', fontSize: 21, fontWeight: 700, letterSpacing: '-0.02em', color: 'var(--text-1)', margin: 0 },
  subheading: { fontSize: 'var(--fs-body)', color: 'var(--text-2)', marginTop: 7, lineHeight: 1.55 },
  tabs: {
    display: 'flex', gap: 4, marginTop: 22, marginBottom: 22,
    background: 'var(--surface-2)', padding: 3,
    borderRadius: 'var(--r-md)', border: '1px solid var(--border)',
  },
  tab: {
    flex: 1, padding: '7px 12px', borderRadius: 'var(--r-sm)', border: 'none',
    background: 'transparent', color: 'var(--text-3)',
    fontSize: 12.5, fontWeight: 600, fontFamily: 'var(--font-body)',
    cursor: 'pointer', transition: 'all 0.2s',
  },
  tabActive: { background: 'var(--surface-hover)', color: 'var(--text-1)', boxShadow: 'inset 0 0 0 1px var(--border-bright)' },
  fieldGroup: { display: 'flex', flexDirection: 'column', gap: 7, marginBottom: 16 },
  label: { fontSize: 11, fontWeight: 600, color: 'var(--text-3)', letterSpacing: '0.07em', textTransform: 'uppercase' },
  optional: { textTransform: 'none', letterSpacing: 0, fontWeight: 500, opacity: 0.7 },
  input: {
    width: '100%', border: '1px solid var(--border-bright)', borderRadius: 'var(--r-md)',
    padding: '10px 13px', fontSize: 'var(--fs-body)', color: 'var(--text-1)',
    background: 'var(--surface-3)', outline: 'none', fontFamily: 'var(--font-body)',
  },
  helper: { fontSize: 11, lineHeight: 1.4 },
  error: {
    background: 'rgba(251,113,133,0.08)', color: 'var(--accent-rose)',
    border: '1px solid rgba(251,113,133,0.22)', borderRadius: 'var(--r-md)',
    padding: '10px 12px', fontSize: 'var(--fs-sm)', lineHeight: 1.5, marginBottom: 16,
  },
  submit: {
    display: 'inline-flex', alignItems: 'center', justifyContent: 'center', gap: 8,
    width: '100%', marginTop: 4, padding: '11px 18px',
    background: 'var(--action)', color: 'var(--action-text)', border: 'none',
    borderRadius: 'var(--r-md)', fontFamily: 'var(--font-body)',
    fontSize: 'var(--fs-body)', fontWeight: 600, cursor: 'pointer',
    transition: 'background 0.15s ease, opacity 0.15s ease',
  },
  submitDisabled: { opacity: 0.35, cursor: 'not-allowed' },
  footnote: { fontSize: 11, color: 'var(--text-3)', lineHeight: 1.5, marginTop: 18, textAlign: 'center' },
};
