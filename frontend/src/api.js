// BASE가 비어 있으면 Vite 프록시(/chat → localhost:8000) 사용
const BASE = import.meta.env.VITE_API_URL ?? '';

// ─── Mock 데이터 ───────────────────────────────────────────────────────────────
const MOCK_IPO_ITEMS = [
  { name: '엔젤로보틱스',      start: '2026-07-01', end: '2026-07-02', price: 45000,  underwriter: '미래에셋증권' },
  { name: 'HD현대마린솔루션',  start: '2026-07-07', end: '2026-07-08', price: 83700,  underwriter: 'KB증권'      },
  { name: '케이뱅크',          start: '2026-07-14', end: '2026-07-15', price: 10000,  underwriter: '삼성증권'    },
];

let mockSchedules = [
  { id: 1, title: '엔젤로보틱스 청약 신청 메모',  datetime: '2026-07-01T09:00:00' },
  { id: 2, title: '증권계좌 잔액 확인',            datetime: '2026-07-06T10:00:00' },
];
let nextMockId = 3;

function mockColbyReply(msg) {
  const m = msg.toLowerCase();
  if (m.includes('일정') || m.includes('청약') || m.includes('ipo'))
    return '이번 달 공모주 청약 일정이에요! 엔젤로보틱스(7/1~2), HD현대마린솔루션(7/7~8), 케이뱅크(7/14~15)가 있어요. 아래 카드도 확인해보세요 😊';
  if (m.includes('공모주') || m.includes('주식'))
    return '공모주란 기업이 주식을 처음 일반 투자자에게 파는 거예요! 청약 기간에 증권사에서 신청하면 추첨으로 받을 수 있어요 🎲\n단, 투자 판단은 꼭 직접 해주세요!';
  if (m.includes('절차') || m.includes('방법') || m.includes('어떻게'))
    return '청약 절차는 이래요!\n1️⃣ 청약 전날까지 주관 증권사 계좌 개설\n2️⃣ 청약 기간에 HTS·MTS로 신청\n3️⃣ 청약 증거금 납입 (공모가 × 수량 × 50%)\n4️⃣ 배정 결과 확인 후 잔금 자동 처리\n어렵지 않죠? 콜비가 항상 옆에 있을게요 🕵️';
  if (m.includes('안녕') || m.includes('hi') || m.includes('hello'))
    return '안녕하세요! 저는 공모주 꼬마 탐정 콜비예요 🕵️ 공모주 일정·청약 방법·개념 등 뭐든 물어보세요!';
  return `"${msg}" — 알겠어요! 지금은 백엔드 연결 전 Mock 모드예요 🔧\n공모주 일정·청약 절차·개념 등을 물어보세요!`;
}

function delay(ms) { return new Promise((r) => setTimeout(r, ms)); }

// ─── POST /chat ────────────────────────────────────────────────────────────────
export async function postChat(session_id, message) {
  try {
    const res = await fetch(`${BASE}/chat`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ session_id, message }),
    });
    if (!res.ok) throw new Error(res.statusText);
    return await res.json();
  } catch {
    await delay(700);
    const isScheduleQ = ['일정', '청약', 'ipo'].some((k) => message.includes(k));
    return {
      answer_text: mockColbyReply(message),
      sources: isScheduleQ ? MOCK_IPO_ITEMS.slice(0, 2) : [],
      usage: { model: 'mock', input_tokens: 48, output_tokens: 92, cost_usd: 0 },
      latency_ms: 700,
    };
  }
}

// ─── POST /stt ─────────────────────────────────────────────────────────────────
// audioBlob: MediaRecorder가 만든 오디오 Blob (webm/opus 등).
// 실패 시 mock으로 대체하지 않고 그대로 throw — 호출부(ColbyAvatarPage)에서
// catch해서 idle 복귀 + 에러 메시지 표시를 책임진다.
export async function postStt(audioBlob, session_id = '') {
  const form = new FormData();
  form.append('audio', audioBlob, 'audio.webm');
  form.append('session_id', session_id);

  const res = await fetch(`${BASE}/stt`, {
    method: 'POST',
    body: form,
  });
  if (!res.ok) throw new Error(`STT 요청 실패: ${res.status} ${res.statusText}`);
  return await res.json(); // { text }
}

// ─── POST /tts ─────────────────────────────────────────────────────────────────
// 응답이 JSON이 아니라 audio/mpeg 바이너리이므로 blob으로 받는다.
// 실패 시 mock으로 대체하지 않고 그대로 throw.
export async function postTts(text) {
  const res = await fetch(`${BASE}/tts`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ text }),
  });
  if (!res.ok) throw new Error(`TTS 요청 실패: ${res.status} ${res.statusText}`);
  return await res.blob(); // audio/mpeg Blob
}

// ─── GET /ipo/schedule ─────────────────────────────────────────────────────────
export async function getIpoSchedule(range = 'all') {
  try {
    const res = await fetch(`${BASE}/ipo/schedule?range=${range}`);
    if (!res.ok) throw new Error(res.statusText);
    return await res.json();
  } catch {
    await delay(300);
    return { today: '2026-07-01', count: MOCK_IPO_ITEMS.length, items: MOCK_IPO_ITEMS };
  }
}

// ─── GET /schedules ────────────────────────────────────────────────────────────
export async function getSchedules(date) {
  try {
    const url = `${BASE}/schedules${date ? `?date=${date}` : ''}`;
    const res = await fetch(url);
    if (!res.ok) throw new Error(res.statusText);
    return await res.json();
  } catch {
    await delay(200);
    return [...mockSchedules];
  }
}

// ─── POST /schedules ───────────────────────────────────────────────────────────
export async function createSchedule(title, datetime) {
  try {
    const res = await fetch(`${BASE}/schedules`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ title, datetime }),
    });
    if (!res.ok) throw new Error(res.statusText);
    return await res.json();
  } catch {
    const item = { id: nextMockId++, title, datetime };
    mockSchedules.push(item);
    return item;
  }
}

// ─── PUT /schedules/:id ────────────────────────────────────────────────────────
export async function updateSchedule(id, title, datetime) {
  try {
    const res = await fetch(`${BASE}/schedules/${id}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ title, datetime }),
    });
    if (!res.ok) throw new Error(res.statusText);
    return await res.json();
  } catch {
    mockSchedules = mockSchedules.map((s) => (s.id === id ? { ...s, title, datetime } : s));
    return mockSchedules.find((s) => s.id === id);
  }
}

// ─── DELETE /schedules/:id ─────────────────────────────────────────────────────
export async function deleteSchedule(id) {
  try {
    const res = await fetch(`${BASE}/schedules/${id}`, { method: 'DELETE' });
    if (!res.ok) throw new Error(res.statusText);
  } catch {
    mockSchedules = mockSchedules.filter((s) => s.id !== id);
  }
}
