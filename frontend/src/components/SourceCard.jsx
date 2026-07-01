export default function SourceCard({ item }) {
  return (
    <div className="source-card">
      <p className="source-name">📋 {item.name}</p>
      <div className="source-details">
        <span>📅 {item.start} ~ {item.end}</span>
        {item.price != null && <span>💰 {item.price.toLocaleString()}원</span>}
        {item.underwriter && <span>🏦 {item.underwriter}</span>}
      </div>
    </div>
  );
}
