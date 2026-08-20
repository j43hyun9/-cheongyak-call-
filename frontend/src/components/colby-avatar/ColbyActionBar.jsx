import { COLBY_STATES } from './useColbyState';

// 화면 하단 액션바 — 큰 마이크 버튼 + 텍스트 입력.
// 마이크 클릭 1회차: 녹음 시작(listening), 2회차: 녹음 종료 → STT/chat/TTS 파이프라인
// 실행(부모 ColbyAvatarPage가 담당). 처리 중(thinking/speaking)에는 버튼 비활성화.
export default function ColbyActionBar({ state, input, onInputChange, onSend, onMicClick }) {
  const busy = state === COLBY_STATES.THINKING || state === COLBY_STATES.SPEAKING;
  const listening = state === COLBY_STATES.LISTENING;

  const handleKeyDown = (e) => {
    if (e.key === 'Enter') onSend();
  };

  return (
    <div className="colby-hub__action-bar">
      <button
        className={`colby-hub__mic-btn${listening ? ' colby-hub__mic-btn--active' : ''}`}
        onClick={onMicClick}
        disabled={busy}
        title={listening ? '말을 마쳤으면 다시 클릭' : '마이크로 말하기'}
      >
        🎤
      </button>
      <p className="colby-hub__mic-hint">
        {listening ? '듣고 있어요...\n다시 눌러서 말 끝내기' : '콜비에게 말해보세요'}
      </p>

      <div className="colby-hub__text-input">
        <input
          type="text"
          value={input}
          onChange={(e) => onInputChange(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="또는 텍스트로 입력해보세요"
          disabled={busy || listening}
        />
        <button onClick={onSend} disabled={busy || listening || !input.trim()}>
          전송
        </button>
      </div>
    </div>
  );
}
