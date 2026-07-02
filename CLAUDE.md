# 청약콜 C팀 2차 — 팀 공통 맥락 (CLAUDE.md)

> 이 파일은 레포 루트에 두고 커밋합니다. 팀원이 `git pull` 하면 각자 Claude Code가 자동으로 읽어요.
> **작업 지시 방법:** 본인 담당 인계점 + 할 일만 명시하면 됩니다 (예: "backend/persona/colbi.py의 SYSTEM_PROMPT를 아래 카드로 교체해줘"). 먼저 계획 요약 받고 단계별 진행 → feature 브랜치 push → PR.
> **변경 시:** 규격/구조가 바뀌면 이 파일을 갱신 커밋하고 팀에 공지. "현재 develop 상태" 섹션은 머지될 때마다 갱신.

## 프로젝트
- 공모주 페르소나 챗봇 **"콜비"** (11살 꼬마 안내자, 코난풍). 공모주 일정 안내 + 개념·절차 설명.
- **투자 판단·권유·수익 보장 절대 금지** (안내자 역할).
- 목표: LLM 페르소나 + 웹 UI 챗봇(필수). 일정 CRUD·캘린더(추가). 로그인은 시간 여유 시(현재 단일 사용자, 인증 없음).

## 환경
- GitHub: https://github.com/j43hyun9/-cheongyak-call-  · 운영 브랜치: **develop**
- 로컬 경로: `C:\AI_Human\teamproject\project2`
- 실행: `uvicorn backend.main:app --reload --port 8000`
- 스택: Python 3.11 / FastAPI / SQLite(aiosqlite) / **OpenAI gpt-4o-mini** / BeautifulSoup4(38.co.kr 크롤러)

## 백엔드 파일 구조 (backend/ 만 정식)
> 구버전 스캐폴드(루트 main.py, api/, core/, db/, services/)는 삭제됨. **참조 금지.**
```
backend/
├── main.py          FastAPI 진입점 (라우터·CORS·lifespan 통합)
├── config.py        pydantic-settings (.env: LLM_ENGINE·OPENAI_API_KEY 등)
├── cache.py         SHA-256 인메모리 응답 캐시 (TTL=1h)
├── llm.py           AsyncOpenAI 호출 추상화 (engine: openai / perso / local)
├── ipo_crawler.py   38.co.kr 공모주 크롤러 (asyncio.to_thread, 15분 캐시, EUC-KR)
├── db.py            SQLite CRUD: call_log·conversation·ipo_cache·schedules
└── persona/colbi.py build_messages(history, user_message, ipo_context) → OpenAI 메시지 리스트
```

## API 계약 v0 — 절대 기준 (변경 시 팀 공유 후)
```
POST /chat   req {session_id, message}
             res {reply, sources[], usage{model,input_tokens,output_tokens,cost_usd}, latency_ms}
GET  /ipo/schedule?range=today|this_week|next_week|all
             res {today, count, items[{name,start,end,price,underwriter}]}
POST /schedules {title, datetime} → {id,title,datetime}
GET  /schedules?date=YYYY-MM-DD   → [{id,title,datetime}]
PUT  /schedules/{id} {title?,datetime?} → {id,title,datetime}
DELETE /schedules/{id}            → {ok:true}
에러: {"error":{"code","message"}}
```

## GitFlow 규칙
- develop 직접 커밋 금지. **feature/XXX → PR → merge.**
- 순서: `git checkout develop && git pull` → `git checkout -b feature/기능명` → 작업 → push → PR (제목에 담당자명)
- 커밋: feat / fix / refactor / chore / docs : 한 줄 설명

## 현재 develop 상태 (머지 기준 — 바뀔 때 갱신)
- ✅ 병합됨: `feature/backend-colby-api`(/chat·/ipo/schedule·CRUD·크롤러·캐시), `feature/db-sqlite`(김준서 — conversation·ipo_cache CRUD, usage_summary), `feature/add-claude-md`(CLAUDE.md 팀 공통 맥락 추가), `feature/cleanup-backend-structure`(구버전 스캐폴드 삭제), `feature/persona-colbi`(장두호), `feature/frontend-chat`(백승옥)
- ⏳ 머지 대기(PR): 없음

## 팀원 담당 인계점
- **장두호** — `backend/persona/colbi.py` SYSTEM_PROMPT 페르소나 카드 완성 / `backend/main.py _is_ipo_question()` 키워드 조정 가능
- **김준서 (본인)** — `backend/db.py` conversation·ipo_cache CRUD 완료. **`_sessions` 인메모리 → SQLite 이전 예정**
- **전재형** — `backend/llm.py` `engine=="perso"` 블록에 PERSO API 구현 (현재 NotImplementedError)
- **백승옥** — `frontend/` : POST /chat, GET /ipo/schedule, CRUD /schedules 소비 (React 챗UI+캘린더)
- **임강** — 백엔드 리드. 브랜치 리뷰·머지, PERSO 공동

## 주요 설계 결정 (바꾸기 전 임강과 협의)
- IPO RAG: 공모주·청약 등 키워드 감지 시 크롤러 결과를 ipo_context로 자동 주입
- 세션: 현재 메모리 dict `_sessions` → 김준서가 SQLite 이전 예정. **바꾸지 말 것**
- 비용 추정: .env `cost_per_1k_input` / `cost_per_1k_output`
- DB 경로: 루트 `colby.db` (uvicorn 실행 위치 기준)
- 크롤러 인코딩: EUC-KR → `resp.text` 자동 디코딩 후 BeautifulSoup 전달
