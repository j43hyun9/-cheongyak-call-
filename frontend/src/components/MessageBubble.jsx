import SourceCard from './SourceCard';

export default function MessageBubble({ msg }) {
  const isColby = msg.role === 'colby';

  return (
    <div className={`bubble-wrap ${isColby ? 'colby-wrap' : 'user-wrap'}`}>
      {isColby && <span className="avatar">🕵️</span>}

      <div className="bubble-content">
        {isColby && <span className="colby-tag">콜비</span>}

        <div className={`bubble ${isColby ? 'colby' : 'user'}`}>
          <p className="bubble-text">{msg.text}</p>
        </div>

        {isColby && msg.sources?.length > 0 && (
          <div className="sources">
            {msg.sources.map((s, i) => (
              <SourceCard key={i} item={s} />
            ))}
          </div>
        )}

        {isColby && msg.latency_ms != null && (
          <span className="msg-meta">
            {msg.latency_ms}ms · {msg.usage?.model ?? 'mock'}
          </span>
        )}
      </div>

      {!isColby && <span className="avatar user-avatar">👤</span>}
    </div>
  );
}
