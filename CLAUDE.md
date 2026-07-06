# 청약콜 C팀 2차 — 팀 공통 맥락 (CLAUDE.md)

> 이 파일은 레포 루트에 두고 커밋합니다. 팀원이 `git pull` 하면 각자 Claude Code가 자동으로 읽어요.
> **⚠️ 이 파일(CLAUDE.md)은 팀장 전재형이 단독 관리합니다.** 여러 명이 동시에 고치면 충돌나요. 담당·구조·상태 등 바뀔 내용이 있으면 **직접 수정하지 말고 팀장에게 한 줄 요청** → 팀장이 반영·커밋합니다. 각자는 코드/기능 브랜치에 집중.
> **작업 지시 방법:** 본인 담당 인계점 + 할 일만 명시하면 됩니다 (예: "backend/persona/colbi.py의 SYSTEM_PROMPT를 아래 카드로 교체해줘"). 먼저 계획 요약 받고 단계별 진행 → feature 브랜치 push → PR.
> **변경 시:** 규격/구조가 바뀌면 팀장이 이 파일을 갱신 커밋. "현재 develop 상태" 섹션은 머지될 때마다 팀장이 갱신.

## 프로젝트
- 공모주 페르소나 챗봇 **"콜비"** (11살 꼬마 안내자, 코난풍). 공모주 일정 안내 + 개념·절차 설명.
- **투자 판단·권유·수익 보장 절대 금지** (안내자 역할).
- 목표: LLM 페르소나 + 웹 UI 챗봇(필수). 일정 CRUD·캘린더(추가). 로그인은 시간 여유 시(현재 단일 사용자, 인증 없음).

> ### 🔄 방향 전환 (2026-07-02 강사님 피드백 반영 · 팀 합의 완료)
> 2차의 무게중심 = **"데이터 확보 → 파인튜닝"**. 콜비(코난풍) **어투를 로컬 오픈모델에 QLoRA 파인튜닝**으로 학습시키는 게 핵심 과제.
> - **RAG 제거**: 크롤링 일정을 프롬프트에 주입하던 방식(`_is_ipo_question`→`ipo_context`)은 **프로젝트3 기술이라 2차에선 배제** → 삭제. (단 크롤러·`/ipo/schedule`·캘린더는 **UI 기능으로 유지**)
> - **튜닝 방식**: 로컬 오픈모델 **QLoRA**(Colab, Unsloth) 메인. 모델 후보 = **Qwen2.5-7B-Instruct**(무거우면 3B). OpenAI 파인튜닝은 시간부족 시 폴백(데이터셋 재사용).
> - **데이터**: 콜비 어투 "질문→콜비스타일답변" JSONL(~200건). 씨앗 = 기존 few-shot·페르소나카드·평가셋. **평가셋 30문항은 학습 제외(held-out test, 전/후 비교용)**.
> - **서빙**: 어댑터 병합 → GGUF → **Ollama** 로컬 실행 → `llm.py` local 엔진 연결.

## 환경
- GitHub: https://github.com/j43hyun9/-cheongyak-call-  · 운영 브랜치: **develop**
- 로컬 경로: `C:\AI_Human\teamproject\project2`
- 실행: `uvicorn backend.main:app --reload --port 8000`
- 스택: Python 3.11 / FastAPI / SQLite(aiosqlite) / BeautifulSoup4(38.co.kr 크롤러) / **파인튜닝: 로컬 오픈모델(Qwen2.5) QLoRA + Ollama 서빙**
- **엔진 방침(변경): 최종 목표 = 로컬 파인튜닝 모델(`llm.py` local 엔진 = Ollama).** gpt-4o-mini는 개발·검증·폴백용으로만 사용. PERSO는 폐기(2차 범위 밖).

## 백엔드 파일 구조 (backend/ 만 정식)
> 구버전 스캐폴드(루트 main.py, api/, core/, db/, services/)는 삭제됨. **참조 금지.**
```
backend/
├── main.py          FastAPI 진입점 (라우터·CORS·lifespan 통합)
├── config.py        pydantic-settings (.env: LLM_ENGINE·OPENAI_API_KEY 등)
├── cache.py         SHA-256 인메모리 응답 캐시 (TTL=1h)
├── llm.py           엔진 추상화 (engine: local=목표(Ollama 파인튜닝모델) / openai=개발·폴백 / ~~perso 폐기~~)
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
- ✅ 병합 완료: backend-colby-api(/chat·/ipo/schedule·CRUD·크롤러·캐시), db-sqlite(conversation·ipo_cache·usage_summary), cleanup-backend-structure(구버전 스캐폴드 삭제→backend/ 일원화), persona-colbi(장두호 콜비 v5), frontend-chat(백승옥 React 챗UI+캘린더), colbi-tune(장두호 — gpt-4o-mini·IPO 키워드 보강), colbi-char(장두호 — 캐릭터성 강화 v6, 답변 시작 패턴·GREETING), CLAUDE.md
- ✅ 세션 `_sessions` → SQLite conversation 이전 완료 (김준서, PR#6 머지)
- ✅ eval 평가셋 30문항 + 리포트 반영 (`eval/`), 콜비 `PERSONA_VERSION="v6"`
- ✅ **통합 실행 테스트 통과 (2026-07-02)**: /chat + /ipo/schedule(30건) + /schedules CRUD + 비용로그 정상
- 🔄 **방향 전환 (2026-07-03~)**: RAG 제거 + 어투 데이터셋 + QLoRA 파인튜닝 + Ollama 서빙.
- ✅ RAG 제거(PR#7)·local 엔진(PR#8)·전처리 스크립트(PR#9) 머지 완료. ✅ **어투 데이터셋 완료(2026-07-06, 장두호 PR#10 정본)**: `data/colbi_sft.jsonl` 200건(eval 겹침 0), 전처리 → train 180/val 20. colbi.py 오타("스타일인걸") 수정 포함.
- 다음(플랜 ~7/15): ①~~데이터셋~~✅완료 ②**QLoRA 학습(전재형)** ← 지금 여기 ③GGUF→Ollama 서빙 연결(임강) ④프론트 최종 연동(백승옥)

## 팀원 담당 인계점 (2026-07-06 — 데이터셋은 장두호 담당 유지)
- **장두호** — **콜비 어투 데이터셋 담당**(완료: `data/colbi_sft.jsonl` 200건, PR#10) + `colbi.py` 페르소나 어투 유지. 데이터 소스는 장두호가 관리(단일 파일 `colbi_sft.jsonl`).
- **전재형(PM)** — **QLoRA 학습 주도**(Colab, Unsloth+Qwen2.5-7B, `colbi_sft.jsonl` 입력) + 파인튜닝 **전/후 평가 리포트**(평가셋 30 held-out) + 조율·발표·문서. CLAUDE.md 단독 관리.
- **임강(백엔드 리드)** — **RAG 제거**(`main.py`의 `_is_ipo_question`→`ipo_context` 삭제, `/ipo/schedule`·크롤러는 유지) + `backend/llm.py` **local 엔진 구현**(Ollama HTTP 연결) + GGUF→Ollama 서빙 + 리뷰·머지·통합.
- **김준서** — DB·세션 유지(완료) + **크롤러·`/ipo/schedule` 엔드포인트 유지·정리**(캘린더용, 챗봇과 분리) + **데이터 전처리 스크립트**(JSONL 포맷·dedup·train/val split) 지원.
- **백승옥** — `frontend/` : 챗UI·캘린더 유지·연동. 최종적으로 파인튜닝 모델 응답으로 데모(백엔드가 모델 추상화하므로 /chat 계약 그대로). 변동 적음.

## 주요 설계 결정 (바꾸기 전 임강과 협의)
- ~~IPO RAG 자동 주입~~ → **제거**(2026-07-02, 프로젝트3 기술). 크롤러·`/ipo/schedule`·캘린더는 UI 기능으로 유지.
- 파인튜닝: 로컬 오픈모델 QLoRA(Qwen2.5-7B, Colab+Unsloth) → GGUF → Ollama 서빙 → `llm.py` local 엔진. 데이터=`data/colbi_sft.jsonl`(~200건), 평가셋 30은 학습 제외.
- 세션: `_sessions` → SQLite conversation 이전 **완료**(김준서 PR#6).
- 비용 추정: .env `cost_per_1k_input` / `cost_per_1k_output` (개발용 gpt-4o-mini에만 해당)
- DB 경로: 루트 `colby.db` (uvicorn 실행 위치 기준)
- 크롤러 인코딩: EUC-KR → `resp.text` 자동 디코딩 후 BeautifulSoup 전달
