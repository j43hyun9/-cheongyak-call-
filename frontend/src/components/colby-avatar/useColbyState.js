import { useCallback, useState } from 'react';

// AI Human 콜비의 4가지 상태. 문자열 오타 방지를 위해 상수로 export.
export const COLBY_STATES = {
  IDLE: 'idle',
  LISTENING: 'listening',
  THINKING: 'thinking',
  SPEAKING: 'speaking',
};

// 상태값만 관리하는 훅 (UI 로직 없음).
// 추후 STT/TTS/RAG 연동 시 이 훅의 to*() 함수를 아래 순서로 호출하면 됨:
//   마이크 시작 → toListening()
//   음성 입력 종료 → toThinking()
//   FastAPI/RAG 응답 수신 → toSpeaking()
//   TTS 재생 종료 → toIdle()
export default function useColbyState(initialState = COLBY_STATES.IDLE) {
  const [state, setState] = useState(initialState);

  const toIdle = useCallback(() => setState(COLBY_STATES.IDLE), []);
  const toListening = useCallback(() => setState(COLBY_STATES.LISTENING), []);
  const toThinking = useCallback(() => setState(COLBY_STATES.THINKING), []);
  const toSpeaking = useCallback(() => setState(COLBY_STATES.SPEAKING), []);

  return { state, setState, toIdle, toListening, toThinking, toSpeaking };
}
