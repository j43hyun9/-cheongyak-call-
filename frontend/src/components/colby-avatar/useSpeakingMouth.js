import { useEffect, useRef, useState } from 'react';
import { COLBY_STATES } from './useColbyState';

// 볼륨(0~1, RMS) 임계값. 용도가 둘로 나뉜다:
//  - VOLUME_OPEN_THRESHOLD: 오디오 재생 중 1(반개)과 2(열림)을 가르는 기준.
//  - VOLUME_HALF_THRESHOLD: "지금 이 순간이 조용한가"를 판단하는 기준. 다만 이
//    값 아래라고 곧바로 닫히는(0) 건 아니다 — 아래 SILENCE_HANGOVER_MS만큼
//    끊기지 않고 유지돼야 실제로 닫힌다("예상할 수 없어"처럼 조용하게 끝나는
//    단어 한 토막이 이 값 아래를 스칠 수 있어서, 순간값만으로 0을 주면 그
//    단어를 입 닫은 채 말하는 문제가 있었다).
const VOLUME_HALF_THRESHOLD = 0.12;
const VOLUME_OPEN_THRESHOLD = 0.28;

// RMS 급변에 따른 프레임 떨림을 막기 위한 지수이동평균 계수(0~1, 클수록 반응 빠름).
// 상승(발화 시작, attack)과 하강(무음 복귀, release)의 체감 지연이 서로 달라서
// (입이 늦게 닫히는 쪽이 훨씬 눈에 띔) 방향별로 다른 계수를 쓴다 — 오디오
// 컴프레서/보코더에서 흔히 쓰는 attack/release 분리와 같은 원리.
// 이전엔 EMA_ALPHA=0.35 단일값이었는데, 무음 복귀(release)에서 이론상 최대
// ~40ms의 자체 지연이 있었고 여기에 MIN_HOLD_MS까지 겹쳐 "한 박자 늦게" 느껴졌다.
const ATTACK_ALPHA = 0.6;
const RELEASE_ALPHA = 0.85;

// 프레임이 바뀐 뒤 최소 이 시간(ms) 동안은 다시 바뀌지 않도록 하는 hysteresis(디바운스).
// 오직 1↔2(반개/열림) "파닥임" 전환에만 적용된다 — 0에서 다시 열리는 전환은
// 아래 REOPEN_HOLD_MS가 따로 담당한다(둘을 분리한 이유는 REOPEN_HOLD_MS
// 주석 참고). 20ms는 타이밍은 맞았지만 음절마다 입이 너무 자주(파닥파닥)
// 바뀌는 느낌을 줘서, 다시 조금 늘려 변화 빈도를 낮췄다(원래 60ms보다는
// 훨씬 짧게 유지 — 그때의 "늦게 반응함" 문제로 되돌아가지 않는 선).
const MIN_HOLD_MS = 45;

// 0(닫힘) → 1 또는 2로 "다시 열리는" 전환 전용 hold. MIN_HOLD_MS와 굳이
// 분리한 이유: 닫힌 직후 곧바로 다음 발음이 시작되는 경우, MIN_HOLD_MS를
// 그대로 쓰면 이미 소리가 커졌는데도 최대 45ms 동안 입이 닫힌 채로 남아있게
// 된다. 재오픈은 "닫혀 있다가 소리가 다시 커지면" 이라는 명확한 신호가 있어
// 1↔2 파닥임(둘 다 "소리는 계속 나는 중"이라 구분이 모호함)과 달리 즉시
// 반영해도 떨림 걱정이 없다 — 그래서 0에 가깝게 잡는다.
const REOPEN_HOLD_MS = 0;

// "무음 hangover" — 오디오가 재생되는 도중, 신호가 VOLUME_HALF_THRESHOLD
// 아래로 끊기지 않고 이 시간(ms) 이상 계속돼야만 frame 0(완전 닫힘)을
// 허용한다. 노이즈 게이트/VAD의 hangover와 같은 개념: 마지막 전환 이후
// 경과시간이 아니라 "연속 무음 지속시간" 기준이다. 이게 바로 "재생 중
// 파닥임" 느낌을 결정하는 값 — 40ms일 때가 가장 자연스럽다는 피드백을 받아
// 이 값으로 고정했다(150ms로 늘리면 재생 중엔 거의 안 닫혀 밋밋해지고,
// 반대로 END_CLOSE_DELAY_MS와 이 값을 같은 상수로 겸용하면 재생 중 파닥임과
// 오디오 종료 시 여운을 동시에 만족시킬 수 없었다 — 그래서 아래
// END_CLOSE_DELAY_MS로 완전히 분리했다).
//
// "발화 중 짧은 dip"과 "문장이 실제로 끝나는 무음"을 재생 "도중"의 RMS
// 만으로 구분하는 것은(지나봐야 알 수 있어서) 여전히 불가능하다 — 하지만
// "오디오가 완전히 멈췄다"는 audio.onended/SPEAKING→IDLE 전환이라는 명확한
// 이벤트가 따로 있으므로, 그 순간의 마무리 여운은 이 값이 아니라 아래
// END_CLOSE_DELAY_MS가 전담한다.
const IN_SPEECH_CLOSE_MS = 40;

// 오디오가 실제로 끝나(SPEAKING→IDLE 전환) 더 이상 재생 중이 아닐 때, 곧바로
// frame 0으로 뚝 끊지 않고 반개(1)로 열어 보여준 뒤 이 시간(ms) 동안
// 유지했다가 닫는다 — "말이 끝났는데 입만 갑자기 뚝 닫히는" 부자연스러움을
// 줄이기 위한 마무리 여운. IN_SPEECH_CLOSE_MS(재생 중 파닥임)와는 완전히
// 별도 타이머로 처리한다(아래 SPEAKING 이탈 분기 참고) — RMS/EMA와 무관하게
// 단순 setTimeout이라, 재생 중 로직에는 전혀 영향을 주지 않는다. 150ms에서는
// 눈에 잘 안 띄어(특히 직전까지 닫혀 있던 경우와 구분이 잘 안 감) 더 뚜렷이
// 보이도록 늘렸다.
const END_CLOSE_DELAY_MS = 250;

// AnalyserNode의 시간축 버퍼 창(=지연 요소 중 하나)을 512→256으로 줄여
// RMS가 더 최근 오디오를 반영하게 한다. 주파수 해상도는 RMS 계산에 쓰지
// 않으므로 손해가 없다.
const FFT_SIZE = 256;

// SPEAKING 상태일 때, 실제로 재생 중인 TTS <audio> 엘리먼트의 음량(RMS)을
// Web Audio API(AudioContext + MediaElementSource + AnalyserNode)로 실시간 분석해서
// 입 벌림 프레임(0=닫힘|1=반개|2=열림)을 반환하는 훅.
//
// 반환 인터페이스(frameIndex: 0|1|2)는 이전 타이머 버전과 동일하게 유지했다 —
// ColbyAvatar.jsx / colbyCharacterAssets.js는 이 값을 어떻게 만들었는지 몰라도 된다.
//
// audioRef: ColbyAvatarPage에서 TTS 재생에 쓰는 `new Audio(url)` 인스턴스를 담은 ref.
// SPEAKING이 될 때마다 audioRef.current는 해당 발화용으로 새로 생성된 오디오 엘리먼트다
// (매 TTS 응답마다 새 Audio 객체를 만들므로, MediaElementSource를 같은 엘리먼트에
// 두 번 연결하는 일은 없다 — 이는 브라우저가 던지는 InvalidStateError의 원인이 된다).
export default function useSpeakingMouth(state, audioRef) {
  const [frameIndex, setFrameIndex] = useState(0);

  const audioCtxRef = useRef(null);
  const analyserRef = useRef(null);
  const sourceRef = useRef(null);
  const sourceElRef = useRef(null); // 현재 analyser에 연결돼 있는 <audio> 엘리먼트(중복 연결 방지용)
  const dataArrayRef = useRef(null);
  const rafRef = useRef(null);
  const emaRef = useRef(0);
  const frameRef = useRef(0);
  const lastSwitchAtRef = useRef(0);
  const silenceSinceRef = useRef(null); // ema가 VOLUME_HALF_THRESHOLD 아래로 처음 떨어진 시각(연속 무음 지속시간 측정용, 무음이 아니면 null)
  const endCloseTimerRef = useRef(null); // SPEAKING→IDLE 전환 시 마무리 여운(END_CLOSE_DELAY_MS)용 타이머

  // SPEAKING 진입/이탈마다 분석 루프를 시작/정지한다.
  useEffect(() => {
    if (state !== COLBY_STATES.SPEAKING) {
      emaRef.current = 0;
      silenceSinceRef.current = null;
      if (rafRef.current) {
        cancelAnimationFrame(rafRef.current);
        rafRef.current = null;
      }

      // SPEAKING(재생 중이던 상태)→IDLE(오디오 재생 종료)로 넘어온 경우에만
      // 마무리 동작을 한다. IDLE이 아닌 다른 상태로의 전환(방어적 처리, 현재
      // 구조상 SPEAKING의 유일한 도착 상태는 IDLE이라 실제로는 거의 없음)만
      // 지연 없이 즉시 반영한다.
      //
      // 주의: 여기서 "직전 프레임이 이미 0이었으면 건너뛴다"는 예외를 두면
      // 안 된다 — 실제 TTS 오디오는 거의 항상 끝에 약간의 무음 여운이 있어서,
      // audio.onended가 뜨기 직전에 재생 중 판정(IN_SPEECH_CLOSE_MS=40ms)이
      // 먼저 입을 닫혀버리는 경우가 대부분이다. 그 예외를 뒀더니 이 마무리
      // 제스처가 사실상 거의 항상 스킵돼서 "말이 끝나면 계속 닫혀 있는" 것처럼
      // 보였다 — 그래서 직전 프레임과 무관하게 항상 실행한다.
      const isEndOfSpeech = state === COLBY_STATES.IDLE;

      if (!isEndOfSpeech) {
        frameRef.current = 0;
        setFrameIndex(0);
        return undefined;
      }

      // 마무리는 직전 프레임과 무관하게 항상 반개(1)로 한 번 열어 보여준 뒤 닫는다.
      frameRef.current = 1;
      setFrameIndex(1);

      endCloseTimerRef.current = setTimeout(() => {
        frameRef.current = 0;
        setFrameIndex(0);
        endCloseTimerRef.current = null;
      }, END_CLOSE_DELAY_MS);

      return () => {
        if (endCloseTimerRef.current) {
          clearTimeout(endCloseTimerRef.current);
          endCloseTimerRef.current = null;
        }
      };
    }

    const audioEl = audioRef?.current;
    const AudioContextCtor = window.AudioContext || window.webkitAudioContext;

    // 오디오 엘리먼트가 없거나 브라우저가 Web Audio API를 지원하지 않으면
    // 립싱크만 포기하고(입 닫힘 고정) 오디오 재생 자체에는 관여하지 않는다.
    if (!audioEl || !AudioContextCtor) {
      setFrameIndex(0);
      return undefined;
    }

    if (!audioCtxRef.current || audioCtxRef.current.state === 'closed') {
      // 컨텍스트를 새로 만들면 거기 물려 있던 노드는 전부 무효가 되므로 같이 리셋한다.
      // (React.StrictMode는 dev 모드에서 마운트→언마운트→재마운트를 시뮬레이션하며
      // 언마운트 전용 cleanup에서 audioCtx.close()를 한 번 미리 호출해볼 수 있는데,
      // 그 뒤 재마운트에서도 스스로 복구되도록 하기 위한 방어 코드다.)
      audioCtxRef.current = new AudioContextCtor();
      analyserRef.current = null;
      sourceRef.current = null;
      sourceElRef.current = null;
      dataArrayRef.current = null;
    }
    const audioCtx = audioCtxRef.current;

    if (audioCtx.state === 'suspended') {
      audioCtx.resume().catch(() => {});
    }

    if (!analyserRef.current) {
      analyserRef.current = audioCtx.createAnalyser();
      analyserRef.current.fftSize = FFT_SIZE;
      dataArrayRef.current = new Uint8Array(analyserRef.current.fftSize);
    }
    const analyser = analyserRef.current;

    // 새 <audio> 엘리먼트(= 새 TTS 응답)일 때만 새 source 노드를 만든다.
    // createMediaElementSource는 같은 엘리먼트에 두 번 호출하면 예외가 나므로 가드 필요.
    if (sourceElRef.current !== audioEl) {
      try {
        sourceRef.current?.disconnect();

        const source = audioCtx.createMediaElementSource(audioEl);
        source.connect(analyser);
        // analyser는 audio graph의 "중간"이므로, 여기서 destination까지 다시
        // 연결해줘야 스피커로 소리가 나간다(빠뜨리면 립싱크는 되는데 무음이 된다).
        analyser.connect(audioCtx.destination);

        sourceRef.current = source;
        sourceElRef.current = audioEl;
      } catch {
        // source 연결 실패 시 립싱크만 포기 — 오디오는 브라우저 기본 경로로 계속 재생된다.
        setFrameIndex(0);
        return undefined;
      }
    }

    const dataArray = dataArrayRef.current;
    let cancelled = false;

    const tick = () => {
      if (cancelled) return;

      analyser.getByteTimeDomainData(dataArray);

      let sumSquares = 0;
      for (let i = 0; i < dataArray.length; i += 1) {
        const normalized = (dataArray[i] - 128) / 128;
        sumSquares += normalized * normalized;
      }
      const rms = Math.sqrt(sumSquares / dataArray.length);

      const alpha = rms > emaRef.current ? ATTACK_ALPHA : RELEASE_ALPHA;
      emaRef.current = alpha * rms + (1 - alpha) * emaRef.current;

      const now = performance.now();

      // 연속 무음 지속시간을 계속 추적한다("마지막 전환 이후 시간"이 아니라
      // "지금까지 끊기지 않고 조용했던 시간"). 소리가 조금이라도 다시 커지면
      // 즉시 리셋된다 — 그래서 어절 사이 짧은 dip은 절대 IN_SPEECH_CLOSE_MS에
      // 도달하지 못한다.
      if (emaRef.current < VOLUME_HALF_THRESHOLD) {
        if (silenceSinceRef.current === null) silenceSinceRef.current = now;
      } else {
        silenceSinceRef.current = null;
      }
      const silenceMs = silenceSinceRef.current === null ? 0 : now - silenceSinceRef.current;

      if (silenceMs >= IN_SPEECH_CLOSE_MS) {
        // 진짜 무음(문장 사이 쉼 등)이 충분히 지속된 경우에만 완전히 닫는다.
        if (frameRef.current !== 0) {
          frameRef.current = 0;
          lastSwitchAtRef.current = now;
          setFrameIndex(0);
        }
      } else {
        // 아직 무음 hangover에 도달하지 않았다면(=오디오가 사실상 재생 중이라고
        // 간주) frame은 절대 0으로 내려가지 않는다 — 1(반개)과 2(열림) 사이에서만
        // 오간다. 이래야 조용하게 끝나는 단어를 입 닫은 채 말하는 문제가 없다.
        const openTarget = emaRef.current >= VOLUME_OPEN_THRESHOLD ? 2 : 1;
        // 0에서 다시 열리는 전환(reopen)과 1↔2 파닥임은 서로 다른 hold를 쓴다.
        const isReopening = frameRef.current === 0;
        const holdMs = isReopening ? REOPEN_HOLD_MS : MIN_HOLD_MS;
        const holdElapsed = now - lastSwitchAtRef.current >= holdMs;
        if (openTarget !== frameRef.current && holdElapsed) {
          frameRef.current = openTarget;
          lastSwitchAtRef.current = now;
          setFrameIndex(openTarget);
        }
      }

      rafRef.current = requestAnimationFrame(tick);
    };

    rafRef.current = requestAnimationFrame(tick);

    return () => {
      cancelled = true;
      if (rafRef.current) {
        cancelAnimationFrame(rafRef.current);
        rafRef.current = null;
      }
    };
  }, [state, audioRef]);

  // 컴포넌트 언마운트 시 AudioContext/노드를 완전히 정리한다.
  useEffect(() => {
    return () => {
      if (rafRef.current) cancelAnimationFrame(rafRef.current);
      sourceRef.current?.disconnect();
      analyserRef.current?.disconnect();
      audioCtxRef.current?.close().catch(() => {});
    };
  }, []);

  return frameIndex;
}
