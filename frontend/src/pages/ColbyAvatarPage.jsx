import { useState, useRef, useCallback } from 'react';
import ColbyAvatar from '../components/colby-avatar/ColbyAvatar';
import ColbyChatPanel from '../components/colby-avatar/ColbyChatPanel';
import ColbyActionBar from '../components/colby-avatar/ColbyActionBar';
import ColbyDevControls from '../components/colby-avatar/ColbyDevControls';
import useColbyState, { COLBY_STATES } from '../components/colby-avatar/useColbyState';
import { postChat, postTts, postStt } from '../api';

const GREETING = { role: 'colby', text: '안녕하세요!\n공모주 명탐정 콜비예요.' };

export default function ColbyAvatarPage() {
  const { state, setState, toIdle, toThinking, toSpeaking, toListening } = useColbyState();
  const [messages, setMessages] = useState([GREETING]);
  const [input, setInput] = useState('');
  const [ipoItems, setIpoItems] = useState([]);
  const [devMode, setDevMode] = useState(false);
  const [visemeQueue, setVisemeQueue] = useState(null);
  const sessionId = useRef(crypto.randomUUID());
  const mediaRecorderRef = useRef(null);
  const audioChunksRef = useRef([]);

  const playTts = useCallback((text) =>
    new Promise((resolve) => {
      postTts(text)
        .then(({ blob, wordBoundary }) => {
          if (wordBoundary?.length) setVisemeQueue(wordBoundary);

          const url = URL.createObjectURL(blob);
          const audio = new Audio(url);
          audio.onended = () => {
            URL.revokeObjectURL(url);
            setVisemeQueue(null);
            resolve();
          };
          audio.onerror = () => {
            URL.revokeObjectURL(url);
            setVisemeQueue(null);
            resolve();
          };
          audio.play().catch(() => resolve());
        })
        .catch(resolve);
    }), []);

  const runReply = async (userText) => {
    setMessages((prev) => [...prev, { role: 'user', text: userText }]);
    setIpoItems([]);
    toThinking();

    try {
      const data = await postChat(sessionId.current, userText);
      const replyText = data.answer_text;
      setMessages((prev) => [...prev, { role: 'colby', text: replyText }]);
      if (data.sources?.length) setIpoItems(data.sources);
      toSpeaking();
      await playTts(replyText);
    } catch {
      setMessages((prev) => [
        ...prev,
        { role: 'colby', text: '앗, 오류가 발생했어요. 잠시 후 다시 시도해주세요.' },
      ]);
    } finally {
      toIdle();
    }
  };

  const handleSend = () => {
    const text = input.trim();
    if (!text || state === COLBY_STATES.THINKING || state === COLBY_STATES.SPEAKING) return;
    setInput('');
    runReply(text);
  };

  const handleMicClick = async () => {
    if (state === COLBY_STATES.IDLE) {
      try {
        const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
        const mr = new MediaRecorder(stream);
        audioChunksRef.current = [];
        mr.ondataavailable = (e) => { if (e.data.size > 0) audioChunksRef.current.push(e.data); };
        mr.onstop = async () => {
          stream.getTracks().forEach((t) => t.stop());
          const blob = new Blob(audioChunksRef.current, { type: 'audio/webm' });
          toThinking();
          try {
            const { text } = await postStt(blob);
            if (text?.trim()) {
              await runReply(text);
            } else {
              toIdle();
            }
          } catch {
            toIdle();
          }
        };
        mr.start();
        mediaRecorderRef.current = mr;
        toListening();
      } catch {
        alert('마이크 권한이 필요합니다.');
      }
    } else if (state === COLBY_STATES.LISTENING) {
      mediaRecorderRef.current?.stop();
    }
  };

  return (
    <div className="colby-hub">
      <div className="colby-hub__body">
        <ColbyAvatar state={state} visemeQueue={visemeQueue} />
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
