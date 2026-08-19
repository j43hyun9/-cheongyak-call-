import SourceCard from '../SourceCard';

// AI Human 무대 오른쪽의 대화 패널. 기존 SourceCard를 그대로 재사용해
// 공모주 정보 카드가 채팅 화면과 동일한 톤으로 보이게 한다.
export default function ColbyChatPanel({ messages, ipoItems }) {
  return (
    <section className="colby-hub__chat-panel">
      <div className="colby-hub__chat-header">
        <span className="colby-hub__chat-header-icon">🕵️</span>
        <div>
          <p className="colby-hub__chat-header-title">콜비와 대화하기</p>
          <p className="colby-hub__chat-header-sub">공모주 명탐정 AI Human 프로토타입</p>
        </div>
      </div>

      <div className="colby-hub__chat-body">
        {messages.map((m, i) => (
          <div key={i} className={`colby-hub__bubble-wrap colby-hub__bubble-wrap--${m.role}`}>
            {m.role === 'colby' && <span className="colby-hub__bubble-tag">콜비</span>}
            <div className={`colby-hub__bubble colby-hub__bubble--${m.role}`}>{m.text}</div>
          </div>
        ))}

        {ipoItems?.length > 0 && (
          <div className="colby-hub__ipo-cards">
            {ipoItems.map((item, i) => (
              <SourceCard key={i} item={item} />
            ))}
          </div>
        )}
      </div>
    </section>
  );
}
