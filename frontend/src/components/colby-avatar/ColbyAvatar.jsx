import './colby-avatar.css';
import { useEffect, useState } from 'react';
import { COLBY_STATES } from './useColbyState';
import { getColbyImage, getColbyImageFilename } from './colbyCharacterAssets';
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

// AI Human 콜비가 서 있는 좌측 무대(스테이지) 전체를 담당하는 컴포넌트.
// 캐릭터는 CSS로 그리지 않고, src/assets/colby/의 이미지 에셋을 그대로 사용한다.
// 이미지가 아직 없으면 깨진 아이콘 대신 "COLBY CHARACTER ASSET" 플레이스홀더를 보여준다.
export default function ColbyAvatar({ state = COLBY_STATES.IDLE }) {
  const badge = STATE_BADGES[state];
  // speaking일 때만 150~250ms 간격으로 0↔1 전환되는 mouth animation 프레임.
  // 캐릭터가 "무엇인지"(getColbyImage)와 "언제 바뀌는지"(useSpeakingMouth)는
  // 서로 다른 파일이라 완전히 분리되어 있다 — TTS 연동 시 이 훅만 교체하면 됨.
  const mouthFrame = useSpeakingMouth(state);
  const imageSrc = getColbyImage(state, mouthFrame);
  const [imageFailed, setImageFailed] = useState(false);

  useEffect(() => {
    setImageFailed(false);
  }, [imageSrc]);

  const showPlaceholder = !imageSrc || imageFailed;

  return (
    <section className={`colby-hub__stage-panel colby-hub__stage-panel--${state}`}>
      {/* 캐릭터 주변 AI 이펙트 — 캐릭터 이미지와 완전히 분리된 레이어 */}
      <div className="colby-hub__ambient" aria-hidden="true">
        <span className="colby-hub__glow-ring colby-hub__glow-ring--a" />
        <span className="colby-hub__glow-ring colby-hub__glow-ring--b" />

        {state === COLBY_STATES.THINKING && (
          <div className="colby-hub__particles">
            <span />
            <span />
            <span />
            <span />
          </div>
        )}

        {state === COLBY_STATES.SPEAKING && (
          <div className="colby-hub__waveform">
            <span />
            <span />
            <span />
            <span />
            <span />
            <span />
            <span />
          </div>
        )}
      </div>

      {badge && <span className="colby-hub__state-badge">{badge}</span>}

      <p className="colby-hub__status">{STATUS_TEXT[state]}</p>

      {/*
        AI Human Avatar Stage — 실제 콜비 캐릭터 이미지가 들어갈 자리.
        src/assets/colby/에 상태별 파일(colby-idle.png 등)을 넣으면
        코드 수정 없이 자동으로 이 안에 표시된다.
      */}
      <div className="colby-stage">
        <div className="avatar-container">
          {showPlaceholder ? (
            <div className="colby-character-placeholder">
              <span className="colby-character-placeholder-icon">🖼️</span>
              <p className="colby-character-placeholder-title">COLBY CHARACTER ASSET</p>
              <p className="colby-character-placeholder-file">
                src/assets/colby/{getColbyImageFilename(state)}
              </p>
            </div>
          ) : (
            <img
              className="colby-character-image"
              src={imageSrc}
              alt="AI Human 콜비"
              onError={() => setImageFailed(true)}
            />
          )}
        </div>
      </div>
    </section>
  );
}
