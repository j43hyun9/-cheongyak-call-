import './colby-avatar.css';
import { useState } from 'react';
import { COLBY_STATES } from './useColbyState';
import { getColbyImage, getColbyImageFilename, COLBY_MOUTH_FRAMES } from './colbyCharacterAssets';
import useSpeakingMouth from './useSpeakingMouth';

const STATUS_TEXT = {
  [COLBY_STATES.IDLE]: '무엇을 도와드릴까요?',
  [COLBY_STATES.LISTENING]: '듣고 있어요',
  [COLBY_STATES.THINKING]: '공모주 정보를 찾고 있어요',
  [COLBY_STATES.SPEAKING]: 'COLBY가 답변하고 있어요',
};

const STATE_BADGES = {
  [COLBY_STATES.LISTENING]: '🎙️',
  [COLBY_STATES.THINKING]: '🔍',
  [COLBY_STATES.SPEAKING]: '💬',
};

const MOUTH_KEYS = Object.keys(COLBY_MOUTH_FRAMES);

// 9개 프레임을 항상 DOM에 유지 — 마운트 시 한 번만 디코딩, 이후 opacity 토글만
function SpeakingFrames({ mouthKey, visible }) {
  return (
    <div
      className="colby-img-stack"
      style={{ visibility: visible ? 'visible' : 'hidden' }}
    >
      {MOUTH_KEYS.map((key) => (
        <img
          key={key}
          src={getColbyImage(COLBY_STATES.SPEAKING, key)}
          alt={key === 'closed' ? 'AI Human 콜비' : ''}
          className="colby-img-stack__frame"
          style={{ opacity: mouthKey === key ? 1 : 0 }}
        />
      ))}
    </div>
  );
}

function StaticAvatar({ state, visible }) {
  const [failed, setFailed] = useState(false);
  const src = getColbyImage(state);

  if (!src || failed) {
    return (
      <div
        className="colby-character-placeholder"
        style={{ visibility: visible ? 'visible' : 'hidden' }}
      >
        <span className="colby-character-placeholder-icon">🖼️</span>
        <p className="colby-character-placeholder-title">COLBY CHARACTER ASSET</p>
        <p className="colby-character-placeholder-file">
          src/assets/colby/{getColbyImageFilename(state)}
        </p>
      </div>
    );
  }

  return (
    <img
      className="colby-character-image"
      src={src}
      alt="AI Human 콜비"
      style={{ visibility: visible ? 'visible' : 'hidden' }}
      onError={() => setFailed(true)}
    />
  );
}

export default function ColbyAvatar({ state = COLBY_STATES.IDLE, visemeQueue = null }) {
  const badge = STATE_BADGES[state];
  const mouthKey = useSpeakingMouth(state, visemeQueue);
  const isSpeaking = state === COLBY_STATES.SPEAKING;

  return (
    <section className={`colby-hub__stage-panel colby-hub__stage-panel--${state}`}>
      <div className="colby-hub__ambient" aria-hidden="true">
        <span className="colby-hub__glow-ring colby-hub__glow-ring--a" />
        <span className="colby-hub__glow-ring colby-hub__glow-ring--b" />
        {state === COLBY_STATES.THINKING && (
          <div className="colby-hub__particles">
            <span /><span /><span /><span />
          </div>
        )}
        {isSpeaking && (
          <div className="colby-hub__waveform">
            <span /><span /><span /><span /><span /><span /><span />
          </div>
        )}
      </div>

      {badge && <span className="colby-hub__state-badge">{badge}</span>}
      <p className="colby-hub__status">{STATUS_TEXT[state]}</p>

      <div className="colby-stage">
        <div className="avatar-container">
          {/* idle 이미지를 항상 베이스로 표시 — speaking 시 하체 공백 방지 */}
          <StaticAvatar state={isSpeaking ? COLBY_STATES.IDLE : state} visible={true} />
          {/* SpeakingFrames — 항상 DOM 유지, speaking 시 idle 위에 오버레이 */}
          <SpeakingFrames mouthKey={mouthKey} visible={isSpeaking} />
        </div>
      </div>
    </section>
  );
}
