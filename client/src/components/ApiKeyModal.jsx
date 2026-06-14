import React, { useState } from 'react';

const BRAND_LOGO_SRC = '/logo.png';

export default function ApiKeyModal({ onSave }) {
  const [key, setKey] = useState('');

  const handleSubmit = (e) => {
    e.preventDefault();
    if (key.trim()) {
      onSave(key.trim());
    }
  };

  return (
    <div style={styles.backdrop}>
      <div style={styles.card}>
        <div style={styles.header}>
          <div style={styles.logoFrame}>
            <img src={BRAND_LOGO_SRC} alt="MeetScribe" style={styles.logoImage} />
          </div>
          <h2 style={styles.title}>Welcome to MeetScribe</h2>
          <p style={styles.subtitle}>Please enter your Groq API key to get started.</p>
        </div>

        <form onSubmit={handleSubmit} style={styles.form}>
          <div style={styles.inputWrapper}>
            <input
              type="password"
              placeholder="gsk_xxxxxxxxxxxxxxxxxxxx"
              value={key}
              onChange={(e) => setKey(e.target.value)}
              style={styles.input}
              autoFocus
            />
          </div>
          
          <div style={styles.infoBox}>
            <p style={styles.infoText}>
              Your key is stored locally in your browser and is only used to communicate with Groq's APIs.
            </p>
          </div>

          <button type="submit" style={styles.button} disabled={!key.trim()}>
            Start Session
          </button>
        </form>
        
        <a 
          href="https://console.groq.com/keys" 
          target="_blank" 
          rel="noopener noreferrer"
          style={styles.link}
        >
          Get your API key from Groq Console →
        </a>
      </div>
    </div>
  );
}

const styles = {
  backdrop: {
    position: 'fixed',
    inset: 0,
    background: 'rgba(15, 23, 42, 0.6)',
    backdropFilter: 'blur(8px)',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    zIndex: 1000,
    padding: 20,
  },
  card: {
    background: '#ffffff',
    width: '100%',
    maxWidth: 440,
    borderRadius: 24,
    padding: '40px 32px',
    boxShadow: '0 25px 50px -12px rgba(0, 0, 0, 0.25)',
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center',
    textAlign: 'center',
  },
  header: {
    marginBottom: 32,
  },
  logoFrame: {
    width: 112,
    height: 112,
    borderRadius: 28,
    background: 'linear-gradient(180deg, rgba(255,255,255,0.96), rgba(243, 247, 250, 0.98))',
    border: '1px solid rgba(15, 23, 42, 0.08)',
    boxShadow: '0 18px 40px rgba(15, 23, 42, 0.08)',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    marginBottom: 18,
    marginInline: 'auto',
  },
  logoImage: {
    width: 88,
    height: 88,
    objectFit: 'contain',
    display: 'block',
  },
  title: {
    fontFamily: 'var(--font-head)',
    fontSize: 24,
    fontWeight: 700,
    color: 'var(--text-1)',
    marginBottom: 8,
    letterSpacing: '-0.5px',
  },
  subtitle: {
    fontSize: 15,
    color: 'var(--text-2)',
    lineHeight: 1.5,
  },
  form: {
    width: '100%',
    display: 'flex',
    flexDirection: 'column',
    gap: 20,
  },
  inputWrapper: {
    width: '100%',
  },
  input: {
    width: '100%',
    height: 52,
    background: 'var(--neutral)',
    border: '2px solid var(--border)',
    borderRadius: 14,
    padding: '0 20px',
    fontSize: 15,
    fontFamily: 'var(--font-body)',
    transition: 'all 0.2s ease',
    outline: 'none',
  },
  infoBox: {
    background: 'var(--surface-alt)',
    padding: '12px 16px',
    borderRadius: 12,
    border: '1px solid rgba(240, 128, 60, 0.1)',
  },
  infoText: {
    fontSize: 12,
    color: 'var(--text-2)',
    lineHeight: 1.4,
  },
  button: {
    height: 52,
    background: 'var(--primary)',
    color: '#ffffff',
    border: 'none',
    borderRadius: 14,
    fontSize: 16,
    fontWeight: 600,
    cursor: 'pointer',
    transition: 'transform 0.1s active, opacity 0.2s',
    opacity: 1,
  },
  link: {
    marginTop: 24,
    fontSize: 13,
    color: 'var(--primary)',
    textDecoration: 'none',
    fontWeight: 500,
  }
};
