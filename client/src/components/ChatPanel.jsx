import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react';

import { streamChat } from '../api';
import { formatSessionTimestamp } from '../sessionSettings';

const SendIcon = () => (
  <svg width="16" height="16" viewBox="0 0 24 24" fill="none"
    stroke="white" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <line x1="22" y1="2" x2="11" y2="13" />
    <polygon points="22 2 15 22 11 13 2 9 22 2" fill="white" stroke="none" />
  </svg>
);

function renderInline(text) {
  const parts = [];
  const pattern = /`([^`]+)`/g;
  let lastIndex = 0;
  let key = 0;
  let match;

  const pushWithBold = (chunk) => {
    if (!chunk) {
      return;
    }

    const boldPattern = /\*\*(.+?)\*\*/g;
    let chunkLastIndex = 0;
    let boldMatch;

    while ((boldMatch = boldPattern.exec(chunk)) !== null) {
      if (boldMatch.index > chunkLastIndex) {
        parts.push(chunk.slice(chunkLastIndex, boldMatch.index));
      }

      parts.push(
        <strong key={`bold-${key++}`}>
          {boldMatch[1]}
        </strong>
      );
      chunkLastIndex = boldPattern.lastIndex;
    }

    if (chunkLastIndex < chunk.length) {
      parts.push(chunk.slice(chunkLastIndex));
    }
  };

  while ((match = pattern.exec(text)) !== null) {
    if (match.index > lastIndex) {
      pushWithBold(text.slice(lastIndex, match.index));
    }

    parts.push(
      <code key={`code-${key++}`} style={styles.inlineCode}>
        {match[1]}
      </code>
    );
    lastIndex = pattern.lastIndex;
  }

  if (lastIndex < text.length) {
    pushWithBold(text.slice(lastIndex));
  }

  return parts;
}

function normalizeAssistantText(text) {
  return text
    .replace(/\s+\*\*/g, '\n\n**')
    .replace(/\*\*\s+>/g, '**\n>')
    .replace(/\s+>\s+/g, '\n> ')
    .replace(/\s+(\d+\.)\s+/g, '\n$1 ')
    .replace(/\s+-\s+/g, '\n- ')
    .replace(/\n{3,}/g, '\n\n')
    .trim();
}

function renderAssistantContent(text) {
  const normalized = normalizeAssistantText(text);
  const lines = normalized.split('\n').map((line) => line.trimEnd());
  const nodes = [];
  let bulletItems = [];
  let numberedItems = [];
  let quoteLines = [];

  const flushBullets = () => {
    if (!bulletItems.length) {
      return;
    }
    nodes.push(
      <ul key={`bullets-${nodes.length}`} style={styles.list}>
        {bulletItems.map((item, index) => (
          <li key={`${item}-${index}`}>{renderInline(item)}</li>
        ))}
      </ul>
    );
    bulletItems = [];
  };

  const flushNumbers = () => {
    if (!numberedItems.length) {
      return;
    }
    nodes.push(
      <ol key={`numbers-${nodes.length}`} style={styles.list}>
        {numberedItems.map((item, index) => (
          <li key={`${item}-${index}`}>{renderInline(item)}</li>
        ))}
      </ol>
    );
    numberedItems = [];
  };

  const flushQuotes = () => {
    if (!quoteLines.length) {
      return;
    }
    nodes.push(
      <blockquote key={`quotes-${nodes.length}`} style={styles.blockquote}>
        {quoteLines.map((line, index) => (
          <p key={`${line}-${index}`} style={styles.quoteLine}>
            {renderInline(line)}
          </p>
        ))}
      </blockquote>
    );
    quoteLines = [];
  };

  lines.forEach((line, index) => {
    const trimmed = line.trim();
    if (!trimmed) {
      flushBullets();
      flushNumbers();
      flushQuotes();
      return;
    }

    const headingMatch = trimmed.match(/^\*\*(.+?)\*\*$/);
    if (headingMatch) {
      flushBullets();
      flushNumbers();
      flushQuotes();
      nodes.push(
        <div key={`heading-${index}`} style={styles.sectionHeading}>
          {headingMatch[1]}
        </div>
      );
      return;
    }

    if (trimmed.startsWith('>')) {
      flushBullets();
      flushNumbers();
      quoteLines.push(trimmed.replace(/^>\s?/, ''));
      return;
    }

    const bulletMatch = trimmed.match(/^-\s+(.+)$/);
    if (bulletMatch) {
      flushNumbers();
      flushQuotes();
      bulletItems.push(bulletMatch[1]);
      return;
    }

    const numberedMatch = trimmed.match(/^\d+\.\s+(.+)$/);
    if (numberedMatch) {
      flushBullets();
      flushQuotes();
      numberedItems.push(numberedMatch[1]);
      return;
    }

    flushBullets();
    flushNumbers();
    flushQuotes();
    nodes.push(
      <p key={`paragraph-${index}`} style={styles.paragraph}>
        {renderInline(trimmed)}
      </p>
    );
  });

  flushBullets();
  flushNumbers();
  flushQuotes();

  return nodes.length ? nodes : <p style={styles.paragraph}>{text}</p>;
}

const ChatBubble = ({ role, text }) => {
  const isUser = role === 'user';
  return (
    <div style={{
      ...styles.bubbleGroup,
      ...(isUser ? styles.bubbleGroupUser : styles.bubbleGroupAssistant),
    }}>
      <div style={{
        ...styles.bubbleRole,
        ...(isUser ? styles.bubbleRoleUser : styles.bubbleRoleAssistant),
      }}>{isUser ? 'You' : 'Assistant'}</div>
      <div style={isUser ? styles.bubbleUser : styles.bubbleAssistant}>
        {isUser ? text : renderAssistantContent(text)}
      </div>
    </div>
  );
};

const WELCOME_MESSAGE = {
  role: 'assistant',
  text: 'Clicking a suggestion adds it to this chat and streams a detailed answer. You can also type questions directly. The chatbot answers from this current session only (current transcript, meeting memory, and this chat history).',
};

export default function ChatPanel({
  chatMessages,
  pendingMessage,
  fullTranscript,
  hasApiKey,
  setChatMessages,
  settings,
}) {
  const messages = useMemo(
    () => (chatMessages.length > 0 ? chatMessages : [WELCOME_MESSAGE]),
    [chatMessages]
  );
  const [input, setInput] = useState('');
  const [isSending, setIsSending] = useState(false);
  const bodyRef = useRef(null);
  const lastPendingAtRef = useRef(null);

  useEffect(() => {
    if (bodyRef.current) {
      bodyRef.current.scrollTop = bodyRef.current.scrollHeight;
    }
  }, [messages]);

  const buildHistory = useCallback(
    () =>
      chatMessages
        .map((message) => ({ role: message.role, content: message.text }))
        .filter((message) => message.content.trim()),
    [chatMessages]
  );

  const sendMessage = useCallback(async (text, mode = 'chat') => {
    const trimmed = text.trim();
    if (!trimmed || isSending) {
      return;
    }

    if (!hasApiKey) {
      const timestamp = formatSessionTimestamp();
      setChatMessages((prev) => [
        ...prev,
        {
          role: 'assistant',
          text: 'Add your Groq API key in Settings before sending chat messages.',
          time: timestamp.label,
          isoTime: timestamp.iso,
        },
      ]);
      return;
    }

    const history = buildHistory();
    const userTimestamp = formatSessionTimestamp();
    const assistantTimestamp = formatSessionTimestamp();

    setChatMessages((prev) => [
      ...prev,
      {
        role: 'user',
        text: trimmed,
        time: userTimestamp.label,
        isoTime: userTimestamp.iso,
      },
      {
        role: 'assistant',
        text: '',
        time: assistantTimestamp.label,
        isoTime: assistantTimestamp.iso,
      },
    ]);
    setIsSending(true);

    try {
      await streamChat(
        {
          message: trimmed,
          mode,
          history,
          full_transcript: fullTranscript,
          meeting_memory: settings.meetingMemory,
          chat_prompt: settings.chatPrompt,
          detail_prompt: settings.detailPrompt,
          context_window:
            mode === 'suggestion'
              ? settings.detailContextWindow
              : settings.chatContextWindow,
        },
        (token) => {
          setChatMessages((prev) => {
            const next = [...prev];
            const lastIndex = next.length - 1;
            next[lastIndex] = {
              ...next[lastIndex],
              text: `${next[lastIndex].text}${token}`,
            };
            return next;
          });
        }
      );
    } catch {
      setChatMessages((prev) => {
        const next = [...prev];
        const lastIndex = next.length - 1;
        next[lastIndex] = {
          ...next[lastIndex],
          text: 'Chat stream failed. Please try again.',
        };
        return next;
      });
    } finally {
      setIsSending(false);
    }
  }, [
    buildHistory,
    fullTranscript,
    hasApiKey,
    isSending,
    setChatMessages,
    settings.chatContextWindow,
    settings.meetingMemory,
    settings.chatPrompt,
    settings.detailContextWindow,
    settings.detailPrompt,
  ]);

  useEffect(() => {
    if (!pendingMessage) {
      return;
    }

    if (pendingMessage.at === lastPendingAtRef.current) {
      return;
    }

    lastPendingAtRef.current = pendingMessage.at;
    sendMessage(pendingMessage.text, pendingMessage.mode || 'suggestion');
  }, [pendingMessage, sendMessage]);

  const handleSend = () => {
    const trimmed = input.trim();
    if (!trimmed) {
      return;
    }

    setInput('');
    sendMessage(trimmed, 'chat');
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  return (
    <div style={styles.panel}>
      <div style={styles.header}>
        <span style={styles.label}>3. Chat (detailed answers)</span>
      </div>

      <div ref={bodyRef} style={styles.body} className="scrollable">
        <div style={styles.sessionInfo}>This chatbot gives answers from the current session context only.</div>
        {messages.map((message, index) => (
          <ChatBubble key={`${message.isoTime || message.time || 'welcome'}-${index}`} role={message.role} text={message.text} />
        ))}
      </div>

      <div style={styles.inputArea}>
        <textarea
          style={styles.textarea}
          value={input}
          rows={1}
          placeholder="Ask anything..."
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
          onFocus={(e) => {
            e.target.style.borderColor = 'var(--primary)';
            e.target.style.background = '#fff';
          }}
          onBlur={(e) => {
            e.target.style.borderColor = 'var(--border)';
            e.target.style.background = 'var(--neutral)';
          }}
        />
        <button
          style={styles.sendBtn}
          onClick={handleSend}
          disabled={isSending}
          title="Send"
          onMouseEnter={(e) => {
            e.currentTarget.style.background = 'var(--primary-light)';
          }}
          onMouseLeave={(e) => {
            e.currentTarget.style.background = 'var(--primary)';
          }}>
          <SendIcon />
        </button>
      </div>
    </div>
  );
}

const styles = {
  panel: {
    background: 'var(--surface-alt)',
    border: '1px solid var(--border)',
    borderRadius: 20,
    display: 'flex',
    flexDirection: 'column',
    overflow: 'hidden',
    boxShadow: '0 1px 4px rgba(0,0,0,0.04)',
    minHeight: 0,
  },
  header: {
    padding: '16px 20px',
    borderBottom: '1px solid var(--border)',
    flexShrink: 0,
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'flex-start',
    minHeight: 92,
    borderRadius: '20px 20px 0 0',
  },
  label: {
    fontFamily: 'var(--font-head)',
    fontSize: 11,
    fontWeight: 600,
    letterSpacing: '0.08em',
    textTransform: 'uppercase',
    color: 'var(--text-3)',
  },
  body: {
    flex: 1,
    overflowY: 'auto',
    padding: '16px 20px 12px',
    minHeight: 0,
    display: 'flex',
    flexDirection: 'column',
    gap: 10,
  },
  sessionInfo: {
    fontSize: 12,
    color: 'var(--text-2)',
    border: '1px dashed var(--border)',
    borderRadius: 'var(--radius-md)',
    padding: '10px 12px',
    background: 'rgba(255,255,255,0.5)',
    marginBottom: 14,
  },
  bubbleGroup: {
    display: 'flex',
    flexDirection: 'column',
    maxWidth: '88%',
  },
  bubbleGroupUser: {
    alignSelf: 'flex-end',
    alignItems: 'flex-end',
  },
  bubbleGroupAssistant: {
    alignSelf: 'flex-start',
    alignItems: 'flex-start',
  },
  bubbleRole: {
    fontSize: 10,
    fontWeight: 600,
    letterSpacing: '0.08em',
    textTransform: 'uppercase',
    color: 'var(--text-3)',
    marginBottom: 6,
  },
  bubbleRoleUser: {
    textAlign: 'right',
  },
  bubbleRoleAssistant: {
    textAlign: 'left',
  },
  bubbleUser: {
    padding: '11px 14px',
    borderRadius: 'var(--radius-md)',
    fontSize: 13.5,
    lineHeight: 1.65,
    background: 'var(--primary)',
    color: '#ffffff',
    border: '1px solid rgba(0,61,91,0.35)',
    borderTopRightRadius: 6,
    boxShadow: '0 2px 6px rgba(0, 61, 91, 0.16)',
    whiteSpace: 'pre-wrap',
    wordBreak: 'break-word',
  },
  bubbleAssistant: {
    padding: '11px 14px',
    borderRadius: 'var(--radius-md)',
    borderTopLeftRadius: 6,
    fontSize: 13.5,
    lineHeight: 1.65,
    background: 'var(--surface)',
    color: 'var(--text-1)',
    border: '1px solid var(--border)',
    boxShadow: '0 2px 6px rgba(15, 23, 42, 0.06)',
    wordBreak: 'break-word',
  },
  paragraph: {
    margin: '0 0 12px',
  },
  sectionHeading: {
    fontSize: 12,
    fontWeight: 700,
    textTransform: 'uppercase',
    letterSpacing: '0.04em',
    color: 'var(--text-1)',
    marginBottom: 8,
  },
  blockquote: {
    margin: '0 0 12px',
    padding: '10px 12px',
    borderLeft: '3px solid var(--primary)',
    background: 'rgba(0, 61, 91, 0.06)',
    borderRadius: '0 8px 8px 0',
  },
  quoteLine: {
    margin: 0,
  },
  list: {
    margin: '0 0 12px 18px',
    padding: 0,
  },
  inlineCode: {
    background: 'rgba(15, 23, 42, 0.08)',
    borderRadius: 6,
    padding: '1px 5px',
    fontSize: '0.92em',
    fontFamily: 'ui-monospace, SFMono-Regular, Menlo, monospace',
  },
  inputArea: {
    borderTop: '1px solid var(--border)',
    padding: '14px 16px',
    background: 'var(--surface-alt)',
    flexShrink: 0,
    display: 'flex',
    gap: 8,
    alignItems: 'flex-end',
    borderRadius: '0 0 20px 20px',
  },
  textarea: {
    flex: 1,
    background: 'var(--neutral)',
    border: '1.5px solid var(--border)',
    borderRadius: 'var(--radius-pill)',
    padding: '10px 18px',
    fontFamily: 'var(--font-body)',
    fontSize: 13.5,
    color: 'var(--text-1)',
    resize: 'none',
    outline: 'none',
    lineHeight: 1.5,
    minHeight: 42,
    maxHeight: 120,
    transition: 'border-color 0.15s, background 0.15s',
  },
  sendBtn: {
    background: 'var(--primary)',
    border: 'none',
    borderRadius: '50%',
    width: 42,
    height: 42,
    flexShrink: 0,
    cursor: 'pointer',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    transition: 'background 0.15s',
  },
};
