import { COLBY_STATES } from './useColbyState';

const BUTTONS = [
  { state: COLBY_STATES.IDLE, label: 'IDLE' },
  { state: COLBY_STATES.LISTENING, label: 'LISTENING' },
  { state: COLBY_STATES.THINKING, label: 'THINKING' },
  { state: COLBY_STATES.SPEAKING, label: 'SPEAKING' },
];

// 프로토타입 단계 전용 개발자 테스트 컨트롤.
// 실제 STT/TTS/RAG 연동 후에는 이 컴포넌트를 페이지에서 빼기만 하면
// 다른 파일에 영향 없이 통째로 제거된다.
export default function ColbyDevControls({ state, onChange }) {
  return (
    <div className="colby-dev-controls">
      <p className="colby-dev-title">🛠 개발용 상태 테스트</p>
      <div className="colby-dev-buttons">
        {BUTTONS.map((b) => (
          <button
            key={b.state}
            className={state === b.state ? 'active' : ''}
            onClick={() => onChange(b.state)}
          >
            {b.label}
          </button>
        ))}
      </div>
    </div>
  );
}
