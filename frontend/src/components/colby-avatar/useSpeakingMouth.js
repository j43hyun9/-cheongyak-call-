import { useEffect, useRef, useState } from 'react';
import { COLBY_STATES } from './useColbyState';

const VOWEL_MAP = {
  'ㅏ':'open','ㅑ':'open',
  'ㅐ':'ae','ㅒ':'ae',
  'ㅓ':'eo','ㅕ':'eo',
  'ㅔ':'mid','ㅖ':'mid',
  'ㅡ':'eu',
  'ㅣ':'wide','ㅢ':'wide',
  'ㅗ':'round','ㅛ':'round','ㅚ':'round','ㅘ':'round','ㅙ':'round',
  'ㅜ':'pucker','ㅠ':'pucker','ㅟ':'pucker','ㅝ':'pucker','ㅞ':'pucker',
};

// 유니코드 한글 → 중성(모음) 추출
function extractVowel(char) {
  const code = char.charCodeAt(0) - 0xAC00;
  if (code < 0 || code > 11171) return null;
  const jungIdx = Math.floor((code % 588) / 28);
  const JUNGSEONG = ['ㅏ','ㅐ','ㅑ','ㅒ','ㅓ','ㅔ','ㅕ','ㅖ','ㅗ','ㅘ','ㅙ','ㅚ','ㅛ','ㅜ','ㅝ','ㅞ','ㅟ','ㅠ','ㅡ','ㅢ','ㅣ'];
  return JUNGSEONG[jungIdx] ?? null;
}

// 텍스트에서 대표 입 모양 결정 (첫 번째 한글의 모음 기준)
function textToMouthKey(text) {
  for (const char of text) {
    const vowel = extractVowel(char);
    if (vowel) return VOWEL_MAP[vowel] ?? 'mid';
  }
  return 'mid';
}

// visemeQueue: [{offsetMs, text}, ...] — /tts 응답의 word_boundary 배열
export default function useSpeakingMouth(state, visemeQueue = null) {
  const [mouthKey, setMouthKey] = useState('closed');
  const timerRef = useRef(null);
  const stepRef  = useRef(0);
  const timeoutRefs = useRef([]);

  useEffect(() => {
    clearInterval(timerRef.current);
    timeoutRefs.current.forEach(clearTimeout);
    timeoutRefs.current = [];

    if (state !== COLBY_STATES.SPEAKING) {
      setMouthKey('closed');
      stepRef.current = 0;
      return;
    }

    // ── 1순위: WordBoundary 타임스탬프 기반 ──────────────────────────────
    if (visemeQueue && visemeQueue.length > 0) {
      visemeQueue.forEach(({ offsetMs, text }) => {
        const key = textToMouthKey(text);
        const t = setTimeout(() => setMouthKey(key), offsetMs);
        timeoutRefs.current.push(t);
      });
      // 마지막 단어 후 400ms에 닫힘
      const last = visemeQueue[visemeQueue.length - 1];
      const closeT = setTimeout(() => setMouthKey('closed'), last.offsetMs + 400);
      timeoutRefs.current.push(closeT);
      return () => timeoutRefs.current.forEach(clearTimeout);
    }

    // ── 2순위: 고정 바운스 폴백 (visemeQueue 없을 때) ─────────────────────
    const BOUNCE = ['closed', 'mid', 'open', 'round', 'open', 'mid'];
    timerRef.current = setInterval(() => {
      stepRef.current = (stepRef.current + 1) % BOUNCE.length;
      setMouthKey(BOUNCE[stepRef.current]);
    }, 200);
    return () => clearInterval(timerRef.current);
  }, [state, visemeQueue]);

  return mouthKey;
}
