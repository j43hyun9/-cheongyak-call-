import { useState } from 'react';
import ChatPage from './pages/ChatPage';
import CalendarPage from './pages/CalendarPage';
import ColbyAvatarPage from './pages/ColbyAvatarPage';

export default function App() {
  const [tab, setTab] = useState('chat');

  return (
    <div className="app">
      <header className="app-header">
        <div className="header-brand">
          <span className="header-emoji">🕵️</span>
          <div className="header-text">
            <h1>콜비</h1>
            <p>공모주 꼬마 탐정 · 투자 판단은 직접!</p>
          </div>
        </div>
        <nav className="tab-nav">
          <button
            className={tab === 'chat' ? 'active' : ''}
            onClick={() => setTab('chat')}
          >
            💬 채팅
          </button>
          <button
            className={tab === 'calendar' ? 'active' : ''}
            onClick={() => setTab('calendar')}
          >
            📅 캘린더
          </button>
          <button
            className={tab === 'avatar' ? 'active' : ''}
            onClick={() => setTab('avatar')}
          >
            🕵️ AI Human
          </button>
        </nav>
      </header>

      <main className="main-content">
        {tab === 'chat' ? <ChatPage /> : tab === 'calendar' ? <CalendarPage /> : <ColbyAvatarPage />}
      </main>
    </div>
  );
}
