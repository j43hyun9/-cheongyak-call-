import { useEffect, useRef, useState } from 'react';
import ColbyAvatar from '../components/colby-avatar/ColbyAvatar';
import ColbyChatPanel from '../components/colby-avatar/ColbyChatPanel';
import ColbyActionBar from '../components/colby-avatar/ColbyActionBar';
import ColbyDevControls from '../components/colby-avatar/ColbyDevControls';
import useColbyState, { COLBY_STATES } from '../components/colby-avatar/useColbyState';
import { postStt, postChat, postTts } from '../api';

const GREETING = { role: 'colby', text: '안녕하세요!\n공모주 명탐정 콜비예요.' };

function makeSessionId() {
  return typeof crypto !== 'undefined' && crypto.randomUUID
    ? crypto.randomUUID()
    : `session-${Date.now()}`;
}

// AI Human 콜비 실제 파이프라인 화면.
// 마이크 녹음(MediaRecorder) → POST /stt → POST /chat → POST /tts → 오디오 재생
// 순서로 동작한다. 상태 전환은 오디오 재생 이벤트에 연동되며(setTimeout 없음),
// 어느 단계에서 실패하든 idle로 복귀하고 화면에 짧은 에러 메시지를 남긴다.
export default function ColbyAvatarPage() {
  const { state, setState, toIdle, toThinking, toSpeaking, toListening } = useColbyState();
  const [messages, setMessages] = useState([GREETING]);
  const [input, setInput] = useState('');
  const [ipoItems, setIpoItems] = useState([]);
  const [devMode, setDevMode] = useState(false);

  const sessionIdRef = useRef(makeSessionId());
  const mediaRecorderRef = useRef(null);
  const audioChunksRef = useRef([]);
  const streamRef = useRef(null);
  const audioRef = useRef(null);
  const audioUrlRef = useRef(null);

  const stopStreamTracks = () => {
    streamRef.current?.getTracks().forEach((track) => track.stop());
    streamRef.current = null;
  };

  const cleanupAudio = () => {
    if (audioRef.current) {
      audioRef.current.pause();
      audioRef.current.onplaying = null;
      audioRef.current.onended = null;
      audioRef.current.onerror = null;
      audioRef.current = null;
    }
    if (audioUrlRef.current) {
      URL.revokeObjectURL(audioUrlRef.current);
      audioUrlRef.current = null;
    }
  };

  // 언마운트 시 마이크 스트림·오디오 리소스 정리
  useEffect(() => {
    return () => {
      stopStreamTracks();
      cleanupAudio();
    };
  }, []);

  const showError = (text) => {
    setMessages((prev) => [...prev, { role: 'colby', text: `⚠️ ${text}` }]);
  };

  // TTS 요청 → blob 재생 → 재생 시작 시 speaking, 종료/오류 시 idle.
  // Audio ended 이벤트가 idle 전환의 유일한 트리거이며, 임의 setTimeout은 없다.
  const speak = (text) =>
    new Promise((resolve) => {
      postTts(text)
        .then((blob) => {
          cleanupAudio();
          const url = URL.createObjectURL(blob);
          audioUrlRef.current = url;
          const audio = new Audio(url);
          audioRef.current = audio;

          const finish = () => {
            cleanupAudio();
            toIdle();
            resolve();
          };

          audio.onplaying = () => toSpeaking();
          audio.onended = finish;
          audio.onerror = () => {
            showError('오디오 재생에 실패했어요.');
            finish();
          };

          audio.play().catch(() => {
            showError('오디오 재생을 시작할 수 없어요.');
            finish();
          });
        })
        .catch(() => {
          // #15(chat-api-v1)·#18(RAG-/chat 연동)이 develop에 아직 없으므로
          // 이 단계까지는 도달하지 않을 수 있음 — 아래 sendToColby 주석 참고.
          showError('음성 합성(TTS) 요청에 실패했어요.');
          toIdle();
          resolve();
        });
    });

  // POST /chat → answer_text 표시 → speak(answer_text).
  // NOTE: develop 백엔드는 아직 v1 스키마(#15)가 아니라 `reply` 필드를 반환한다.
  // 여기서는 최종 계약대로 `answer_text`만 읽고 `reply`로의 우회(fallback)를
  // 일부러 넣지 않았다 — #15가 develop에 반영되기 전까지는 이 단계에서
  // "콜비가 답변을 만들지 못했어요" 에러로 불일치가 그대로 드러나야 한다.
  const sendToColby = async (userText) => {
    setMessages((prev) => [...prev, { role: 'user', text: userText }]);
    setIpoItems([]);
    toThinking();

    let chatRes;
    try {
      chatRes = await postChat(sessionIdRef.current, userText);
    } catch {
      showError('콜비 응답(chat) 요청에 실패했어요.');
      toIdle();
      return;
    }

    const answerText = chatRes?.answer_text;
    if (!answerText) {
      showError('콜비가 답변을 만들지 못했어요. (백엔드 /chat이 아직 answer_text를 반환하지 않을 수 있어요)');
      toIdle();
      return;
    }

    setMessages((prev) => [...prev, { role: 'colby', text: answerText }]);
    setIpoItems(chatRes?.sources ?? []);

    await speak(answerText);
  };

  // POST /stt → 인식된 텍스트를 사용자 발화로 표시 → sendToColby
  const runVoicePipeline = async (audioBlob) => {
    toThinking();

    let sttText;
    try {
      const sttRes = await postStt(audioBlob, sessionIdRef.current);
      sttText = sttRes?.text?.trim();
    } catch {
      showError('음성 인식(STT) 요청에 실패했어요.');
      toIdle();
      return;
    }

    if (!sttText) {
      showError('음성을 인식하지 못했어요. 다시 시도해주세요.');
      toIdle();
      return;
    }

    await sendToColby(sttText);
  };

  const startRecording = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      streamRef.current = stream;

      const recorder = new MediaRecorder(stream);
      audioChunksRef.current = [];

      recorder.ondataavailable = (e) => {
        if (e.data.size > 0) audioChunksRef.current.push(e.data);
      };

      recorder.onstop = () => {
        stopStreamTracks();
        const blob = new Blob(audioChunksRef.current, {
          type: recorder.mimeType || 'audio/webm',
        });
        audioChunksRef.current = [];
        runVoicePipeline(blob);
      };

      mediaRecorderRef.current = recorder;
      recorder.start();
      toListening();
    } catch {
      showError('마이크 접근에 실패했어요. 브라우저 권한을 확인해주세요.');
      stopStreamTracks();
      toIdle();
    }
  };

  const stopRecording = () => {
    const recorder = mediaRecorderRef.current;
    if (recorder && recorder.state !== 'inactive') {
      recorder.stop();
    }
  };

  const handleMicClick = () => {
    if (state === COLBY_STATES.IDLE) {
      startRecording();
    } else if (state === COLBY_STATES.LISTENING) {
      stopRecording();
    }
  };

  const handleSend = () => {
    const text = input.trim();
    if (!text) return;
    setInput('');
    sendToColby(text);
  };

  return (
    <div className="colby-hub">
      <div className="colby-hub__body">
        <ColbyAvatar state={state} />
        <ColbyChatPanel messages={messages} ipoItems={ipoItems} />
      </div>

      <ColbyActionBar
        state={state}
        input={input}
        onInputChange={setInput}
        onSend={handleSend}
        onMicClick={handleMicClick}
      />

      <button
        type="button"
        className="colby-hub__dev-toggle"
        onClick={() => setDevMode((v) => !v)}
        title="개발용 상태 테스트 패널"
      >
        🛠
      </button>
      {devMode && <ColbyDevControls state={state} onChange={setState} />}
    </div>
  );
}
