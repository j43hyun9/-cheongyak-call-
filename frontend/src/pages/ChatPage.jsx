import { useState, useEffect, useRef } from 'react';
import { postChat } from '../api';
import MessageBubble from '../components/MessageBubble';

const GREETING = {
  role: 'colby',
  text: '안녕하세요! 저는 공모주 꼬마 탐정 콜비예요 🕵️\n청약 일정·절차·개념 등 뭐든 물어보세요!\n(투자 판단은 직접 해주세요 😊)',
  sources: [],
};

const SUGGESTED_QUESTIONS = [
  { icon: '📅', text: '이번 주 공모주 찾아줘' },
  { icon: '❓', text: '청약이 뭐야?' },
  { icon: '🏦', text: '청약은 어떻게 해?' },
  { icon: '💰', text: '최소 얼마 필요해?' },
];

export default function ChatPage() {
  const [messages, setMessages] = useState([]);
  const [input, setInput]       = useState('');
  const [loading, setLoading]   = useState(false);
  const sessionId   = useRef(crypto.randomUUID());
  const bottomRef   = useRef(null);
  const textareaRef = useRef(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, loading]);

  const send = async (override) => {
    const text = (override ?? input).trim();
    if (!text || loading) return;

    setInput('');
    if (textareaRef.current) textareaRef.current.style.height = 'auto';

    setMessages((prev) => [
      ...(prev.length === 0 ? [GREETING] : prev),
      { role: 'user', text, sources: [] },
    ]);
    setLoading(true);

    try {
      const data = await postChat(sessionId.current, text);
      setMessages((prev) => [
        ...prev,
        {
          role: 'colby',
          text: data.reply,
          sources: data.sources ?? [],
          usage: data.usage,
          latency_ms: data.latency_ms,
        },
      ]);
    } catch {
      setMessages((prev) => [
        ...prev,
        { role: 'colby', text: '앗, 오류가 발생했어요. 잠시 후 다시 시도해주세요 😢', sources: [] },
      ]);
    } finally {
      setLoading(false);
    }
  };

  const onKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      send();
    }
  };

  const onInput = (e) => {
    e.target.style.height = 'auto';
    e.target.style.height = `${Math.min(e.target.scrollHeight, 120)}px`;
  };

  return (
    <div className="chat-page">
      <div className="chat-window">
        {messages.length === 0 && !loading ? (
          <div className="empty-state">
            <span className="empty-avatar">🕵️</span>
            <h2 className="empty-title">안녕하세요, 콜비예요!</h2>
            <p className="empty-subtitle">
              공모주 청약 일정과 절차, 궁금한 개념까지 뭐든 물어보세요.
              <br />
              투자 판단은 직접 해주셔야 해요 😊
            </p>
            <div className="suggested-questions">
              <p className="suggested-title">💡 이런 질문 많이 물어봐요</p>
              <div className="suggested-grid">
                {SUGGESTED_QUESTIONS.map((q) => (
                  <button key={q.text} className="suggested-card" onClick={() => send(q.text)}>
                    <span className="suggested-icon">{q.icon}</span>
                    <span>{q.text}</span>
                  </button>
                ))}
              </div>
            </div>
          </div>
        ) : (
          messages.map((msg, i) => <MessageBubble key={i} msg={msg} />)
        )}

        {loading && (
          <div className="bubble-wrap colby-wrap">
            <span className="avatar">🕵️</span>
            <div className="bubble-content">
              <span className="colby-tag">콜비</span>
              <div className="bubble colby">
                <span className="dot" />
                <span className="dot" style={{ animationDelay: '0.2s' }} />
                <span className="dot" style={{ animationDelay: '0.4s' }} />
              </div>
            </div>
          </div>
        )}

        <div ref={bottomRef} />
      </div>

      <div className="input-bar">
        <textarea
          ref={textareaRef}
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={onKeyDown}
          onInput={onInput}
          placeholder="공모주 일정, 청약 방법... 뭐든 물어보세요! (Enter=전송, Shift+Enter=줄바꿈)"
          rows={1}
          disabled={loading}
        />
        <button onClick={() => send()} disabled={loading || !input.trim()}>
          전송
        </button>
      </div>
    </div>
  );
}
