import { useEffect, useRef, useState } from 'react';
import { COLBY_STATES } from './useColbyState';

const DEFAULT_INTERVAL_MS = 300; // 3프레임 바운스 기준 기본값

// 0(닫힘)→1(살짝 벌림)→2(활짝 벌림)→1(살짝 벌림)→반복 순서로
// 자연스럽게 오가는 바운스 시퀀스.
const BOUNCE_SEQUENCE = [0, 1, 2, 1];

// SPEAKING 상태일 때만 입 벌림 프레임(0|1|2)을 반복 전환하는
// "타이밍 전용" 훅. 어떤 이미지 파일을 쓸지는 전혀 모른다(관심사 분리).
//
// 나중에 실제 TTS를 붙일 때는 이 훅 대신, TTS 재생 시작 시점에 프레임을
// 켜고(setInterval 시작) 재생 종료 시점에 끄는 방식으로 그대로 교체하면 된다.
// (오디오 볼륨에 맞춰 더 정교한 립싱크로 확장할 때도 이 훅의 "프레임 번호를
// 반환한다"는 인터페이스만 유지하면 ColbyAvatar.jsx는 수정할 필요 없음.)
export default function useSpeakingMouth(state, intervalMs = DEFAULT_INTERVAL_MS) {
  const [frameIndex, setFrameIndex] = useState(0);
  const timerRef = useRef(null);
  const stepRef = useRef(0);

  useEffect(() => {
    if (state !== COLBY_STATES.SPEAKING) {
      setFrameIndex(0);
      stepRef.current = 0;
      return undefined;
    }

    timerRef.current = setInterval(() => {
      stepRef.current = (stepRef.current + 1) % BOUNCE_SEQUENCE.length;
      setFrameIndex(BOUNCE_SEQUENCE[stepRef.current]);
    }, intervalMs);

    return () => clearInterval(timerRef.current);
  }, [state, intervalMs]);

  return frameIndex;
}
