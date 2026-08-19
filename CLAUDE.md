# 청약콜 C팀 3차 — 팀 공통 맥락 (CLAUDE.md)

> 이 파일은 레포 루트에 두고 커밋합니다. 팀원이 `git pull` 하면 각자 Claude Code가 자동으로 읽어요.
> **⚠️ 이 파일(CLAUDE.md)은 팀장 전재형이 단독 관리합니다.** 여러 명이 동시에 고치면 충돌나요. 담당·구조·상태 등 바뀔 내용이 있으면 **직접 수정하지 말고 팀장에게 한 줄 요청** → 팀장이 반영·커밋합니다. 각자는 코드/기능 브랜치에 집중.
> **작업 지시 방법:** 본인 담당 인계점 + 할 일만 명시하면 됩니다. 먼저 계획 요약 받고 단계별 진행 → feature 브랜치 push → PR.
> **변경 시:** 규격/구조가 바뀌면 팀장이 이 파일을 갱신 커밋. "현재 develop 상태" 섹션은 머지될 때마다 팀장이 갱신.

## 프로젝트 (3차 기준 — 2026-08-11 확정)
- 공모주 **AI Human 비서 "COLBY"** (11살 코난풍 명탐정). RAG 기반 공모주 정보 안내 + 음성 대화.
- **투자 판단·권유·수익 보장 절대 금지** (안내자 역할, 2차 가드레일 계승).
- **3차 목표**: ① FastAPI 모듈화(`/chat`·`/stt`·`/tts`) ② RAG + Vector DB (LangChain·FAISS) ③ AI Human 아바타 + 상태머신(idle→listening→thinking→speaking) ④ Lip Sync / 표정 ⑤ 음성 입출력(Whisper STT · gTTS TTS).
- **MVP**: 사용자가 말함 → 콜비가 듣는 표정 → RAG 답변 → 콜비가 음성으로 말하며 입이 움직임.

> ### ⚠️ 2차 기록 (참고용 — 3차에서 변경됨)
> 2차 무게중심 = QLoRA 파인튜닝 (Qwen2.5-7B → GGUF → Ollama `colbi-qwen`). RAG는 "프로젝트3 기술"이라 2차에선 배제했음.
> **3차에서는 RAG가 핵심 기술로 재도입됨 (2026-08-11 기획 확정).** 2차에서 살려둔 크롤러·`/ipo/schedule`·캘린더가 RAG 데이터 소스.

> ### 🔄 3차 방향 (2026-08-11 확정)
> - **RAG 재도입**: LangChain + FAISS(로컬) + multilingual-MiniLM 임베딩. `colbi.build_messages(ipo_context=)` 인자 부활.
> - **FastAPI 모듈화**: `/chat`(RAG+LLM)·`/stt`(Whisper)·`/tts`(gTTS) 분리.
> - **AI Human**: 콜비 아바타 상태머신 + Lip Sync (TTS 음성에 맞춰 입 모양).
> - **음성**: Whisper STT + gTTS TTS (1차 자산 재활용).
> - **LLM**: `colbi-qwen` (Ollama, 2차 파인튜닝 모델) 그대로 유지.
> - **마감**: 2026-08-21.

## 환경
- GitHub: https://github.com/j43hyun9/-cheongyak-call-  · 운영 브랜치: **develop**
- 로컬 경로: `C:\AI_Human\teamproject\project2`
- 실행: `uvicorn backend.main:app --reload --port 8000`
- 스택: Python 3.11 / FastAPI / SQLite(aiosqlite) / BeautifulSoup4(38.co.kr 크롤러) / **LangChain·FAISS·multilingual-MiniLM(RAG)** / **Whisper(STT)·gTTS(TTS)** / Ollama `colbi-qwen`(LLM)
- **엔진 방침**: LLM = Ollama `colbi-qwen`(로컬 파인튜닝 모델). OpenAI는 폴백용만.

## 백엔드 파일 구조 (backend/ 만 정식)
```
backend/
├── main.py          FastAPI 진입점 (라우터·CORS·lifespan 통합)
├── config.py        pydantic-settings (.env: LLM_ENGINE·OPENAI_API_KEY 등)
├── cache.py         SHA-256 인메모리 응답 캐시 (TTL=1h)
├── llm.py           엔진 추상화 (engine: local=Ollama colbi-qwen / openai=폴백)
├── ipo_crawler.py   38.co.kr 공모주 크롤러 (asyncio.to_thread, 15분 캐시, EUC-KR)
├── db.py            SQLite CRUD: call_log·conversation·ipo_cache·schedules
├── stt.py           Whisper STT (/stt 라우터)
├── tts.py           gTTS TTS (/tts 라우터)
├── rag/             LangChain·FAISS RAG 모듈
│   ├── indexer.py   색인 파이프라인 (청킹·MiniLM·FAISS)
│   └── retriever.py 검색 + colbi.build_messages 주입
└── persona/colbi.py build_messages(history, user_message, ipo_context) → 메시지 리스트
```

## API 계약 v1 — 절대 기준 (변경 시 팀 공유 후)
```
POST /chat   req {session_id, message}
             res {answer_text, audio_url, state, sources[{title,url,snippet}], usage, latency_ms}
POST /stt    req (multipart audio) → {text}
POST /tts    req {text} → audio/mpeg 바이너리 스트리밍
GET  /ipo/schedule?range=today|this_week|next_week|all
             res {today, count, items[{name,start,end,price,underwriter}]}
POST /schedules {title, datetime} → {id,title,datetime}
GET  /schedules?date=YYYY-MM-DD   → [{id,title,datetime}]
PUT  /schedules/{id} {title?,datetime?} → {id,title,datetime}
DELETE /schedules/{id}            → {ok:true}
에러: {"error":{"code","message"}}
```
- **state** = AI Human 아바타 상태 (`idle|listening|thinking|speaking`)
- **audio_url** = TTS 음성 URL (또는 /tts 바이너리 직접 스트림)
- **sources** = RAG 검색 근거 (문서명·스니펫·type)

## GitFlow 규칙
- develop 직접 커밋 금지. **feature/XXX → PR → merge.**
- 순서: `git checkout develop && git pull` → `git checkout -b feature/기능명` → 작업 → push → PR (제목에 담당자명)
- 커밋: feat / fix / refactor / chore / docs : 한 줄 설명

## 현재 develop 상태 (머지 기준 — 바뀔 때 갱신, 2026-08-19 기준)
- ✅ 2차 기반 (유지): /chat·/ipo/schedule·CRUD·크롤러·캐시·SQLite·페르소나 v6·QLoRA 데이터셋·Ollama local 엔진
- ✅ STT 고도화·FastAPI 연결 (임강, PR#13·#14)
- ✅ TTS 고도화·/tts 백엔드 통합 (김준서·임강, PR#17)
- ✅ RAG backend/rag 이동·슬랭 개선·colbi-qwen 검증 (장두호, PR#16)
- ⏳ **대기 중 (머지 순서 엄수)**:
  - PR#15 `/chat` v1 스키마 (`answer_text`·`audio_url`·`state`) — 임강
  - PR#18 RAG·/chat 연동·크래시버그 수정 — 임강·장두호
  - PR#19 AI Human 프론트·아바타·상태머신·Lip Sync — 백승옥 *(#15 머지 후 같이 또는 직후)*
- 🔜 **머지 후 남은 작업**: STT→/chat(RAG)→TTS→아바타 립싱크 실제 API 연결 (백승옥)

## 팀원 담당 인계점 (2026-08-11 3차 기준)
- **전재형(PM)** — FastAPI 구조 / API 설계 / 전체 통합 / 발표·문서. CLAUDE.md 단독 관리.
- **장두호** — RAG / Vector DB / LLM Persona. `backend/rag/` + `colbi.py` + 색인·retriever.
- **임강(백엔드 리드)** — STT 고도화(`/stt`) / FastAPI 연결 / PR 리뷰·머지·통합. `/chat` v1 스키마.
- **김준서** — TTS 고도화(`/tts`) / 음성 출력 연동.
- **백승옥** — AI Human COLBY 프론트 / 아바타·상태머신·Lip Sync. PR#19 완료, 실제 API 연결 대기 중.

## 주요 설계 결정
- **RAG**: LangChain + FAISS(로컬) + multilingual-MiniLM. `colbi.build_messages(ipo_context=)` 재활용. 소스 = 크롤러 공모주 데이터 + 개념 문서.
- **AI Human**: 2D 이미지 스왑 방식(볼륨 기반 On/Off) — 3D/viseme는 난이도 과다.
- **통신**: 동기 요청/응답 `/chat` 한 번에 반환 — WebSocket/SSE 스트리밍 사용 안 함.
- **LLM**: Ollama `colbi-qwen` (2차 파인튜닝 모델 그대로). OpenAI는 폴백.
- **세션**: SQLite conversation (김준서 PR#6 완료).
- **DB 경로**: 루트 `colby.db` (uvicorn 실행 위치 기준).
- **크롤러 인코딩**: EUC-KR → `resp.text` 자동 디코딩 후 BeautifulSoup 전달.
