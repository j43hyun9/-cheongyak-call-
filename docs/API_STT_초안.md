# `/stt` API 계약 초안 (v1-draft)

> 작성: 임강 (3차 STT/FastAPI 담당) · 2026-08-13
> 상태: **초안 — 팀 합의 전.** 3차 기획서(v0.3) 섹션 7의 `POST /stt (audio) → {text}` 스켈레톤을 구체화한 버전.
> 확정되면 PM(전재형)이 CLAUDE.md의 "API 계약" 절대 기준에 반영.

## 엔드포인트

`POST /stt`

## Request — `multipart/form-data`

| 필드 | 타입 | 필수 | 설명 |
|---|---|---|---|
| `audio` | file | ✅ | 오디오 파일. 브라우저 MediaRecorder 기준 `audio/webm` 또는 `audio/wav` |
| `session_id` | string | ❌ | 로깅/컨텍스트용 (있으면 call_log에 STT 소요시간도 남김) |

## Response — 성공

```json
{ "text": "삼성전자 청약 일정 알려줘" }
```

## Response — 실패

2차 `backend/main.py`의 `err()` 컨벤션 재사용:

```json
{ "error": { "code": "STT_EMPTY_AUDIO" | "STT_UNSUPPORTED_FORMAT" | "STT_FAILED", "message": "..." } }
```

## 설계 메모

- `backend/llm.py`가 `engine: openai/local/perso`로 추상화된 것처럼, STT도 `settings.stt_engine`(`openai`=Whisper API / `local`=faster-whisper, CPU)로 열어둠. 두 엔진 모두 구현 완료 — `local`은 `STT_LOCAL_MODEL`(기본 `base`)로 모델 크기 조절, GPU 없는 팀 환경 가정해 `device="cpu", compute_type="int8"` 고정.
- 1차 `stt.py`의 `prompt="공모주, 청약, 등록, 일정, 회의 관련 명령입니다."` 힌트(도메인 특화 환각 방지)는 그대로 이식.
- 미확정 사항 — PM/프론트와 확인 필요: STT 결과를 `/chat`으로 넘기는 흐름을 **프론트가 조합**(STT 호출 → 받은 text로 `/chat` 재호출)할지, 아니면 **`/stt`가 내부적으로 `/chat`까지 체이닝**할지.
