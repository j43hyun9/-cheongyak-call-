const RAG_TYPE_LABEL = {
  schedule: '📅 일정',
  concept: '📖 개념',
};

function isHttpUrl(url) {
  return typeof url === 'string' && /^https?:\/\//.test(url);
}

// /chat이 반환하는 RAG 검색 결과({title, snippet, type, url})와
// /ipo/schedule이 반환하는 공모주 일정({name, start, end, price, underwriter})은
// 서로 다른 데이터 구조라, 어떤 모양인지 보고 분기해서 렌더링한다.
// (다른 필드로는 판별 오탐 여지가 있어 RAG 전용 필드인 title 유무로 구분)
function isRagSource(item) {
  return item != null && typeof item.title === 'string';
}

function RagSourceCard({ item }) {
  return (
    <div className="source-card">
      <p className="source-name">
        {RAG_TYPE_LABEL[item.type] ?? '📋'} {item.title}
      </p>
      {item.snippet && <p className="source-snippet">{item.snippet}</p>}
      {isHttpUrl(item.url) && (
        <a className="source-link" href={item.url} target="_blank" rel="noreferrer">
          원문 보기 →
        </a>
      )}
    </div>
  );
}

function IpoScheduleCard({ item }) {
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

export default function SourceCard({ item }) {
  if (!item) return null;
  return isRagSource(item) ? <RagSourceCard item={item} /> : <IpoScheduleCard item={item} />;
}
