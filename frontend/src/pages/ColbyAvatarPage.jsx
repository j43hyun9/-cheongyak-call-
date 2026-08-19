import { useState } from 'react';
import ColbyAvatar from '../components/colby-avatar/ColbyAvatar';
import ColbyChatPanel from '../components/colby-avatar/ColbyChatPanel';
import ColbyActionBar from '../components/colby-avatar/ColbyActionBar';
import ColbyDevControls from '../components/colby-avatar/ColbyDevControls';
import useColbyState, { COLBY_STATES } from '../components/colby-avatar/useColbyState';

const GREETING = { role: 'colby', text: '안녕하세요!\n공모주 명탐정 콜비예요.' };
const DEMO_QUESTION = '이번 주 공모주 알려줘';
const DEMO_REPLY = '잠시만요, 제가 찾아볼게요! 이번 주 공모주는 이거예요 🔍';
const DEMO_IPO_ITEMS = [
  { name: '엔젤로보틱스', start: '2026-08-11', end: '2026-08-12', price: 45000, underwriter: '미래에셋증권' },
];

// AI Human 콜비 프로토타입 화면.
// 아직 실제 STT/TTS/RAG를 연결하지 않았으므로, 마이크·텍스트 입력은
// 정해진 데모 문장으로 상태 전환 흐름만 미리 보여준다 (네트워크 호출 없음).
export default function ColbyAvatarPage() {
  const { state, setState, toIdle, toThinking, toSpeaking, toListening } = useColbyState();
  const [messages, setMessages] = useState([GREETING]);
  const [input, setInput] = useState('');
  const [ipoItems, setIpoItems] = useState([]);
  const [devMode, setDevMode] = useState(false);

  const runDemoReply = (userText) => {
    setMessages((prev) => [...prev, { role: 'user', text: userText }]);
    setIpoItems([]);
    toThinking();

    setTimeout(() => {
      toSpeaking();
      setMessages((prev) => [...prev, { role: 'colby', text: DEMO_REPLY }]);
      setIpoItems(DEMO_IPO_ITEMS);

      setTimeout(() => toIdle(), 2200);
    }, 1200);
  };

  const handleSend = () => {
    const text = input.trim();
    if (!text) return;
    setInput('');
    runDemoReply(text);
  };

  const handleMicClick = () => {
    if (state === COLBY_STATES.IDLE) {
      toListening();
    } else if (state === COLBY_STATES.LISTENING) {
      runDemoReply(DEMO_QUESTION);
    }
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
