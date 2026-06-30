import uuid
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from core.llm import call_llm
from core.persona import get_system_prompt
from services import cache, call_logger

router = APIRouter(prefix="/chat", tags=["chat"])

# 세션별 대화 이력 (메모리 임시 저장)
# 김준서가 SQLite conversation 테이블로 이전 예정
_sessions: dict[str, list[dict]] = {}
_MAX_HISTORY_TURNS = 10  # 최근 N턴만 컨텍스트로 유지 (프롬프트 다이어트)


class ChatRequest(BaseModel):
    message: str
    session_id: str = ""
    ipo_context: str = ""  # 장두호가 크롤러 결과를 RAG로 주입하는 슬롯


class ChatResponse(BaseModel):
    reply: str
    session_id: str
    elapsed_ms: int
    cache_hit: bool


@router.post("", response_model=ChatResponse)
async def chat(req: ChatRequest):
    if not req.message.strip():
        raise HTTPException(status_code=400, detail="message가 비어 있습니다.")

    session_id = req.session_id or str(uuid.uuid4())

    # ── 1. 캐시 확인 ──────────────────────────────────────
    cached_reply = cache.get(req.message)
    if cached_reply:
        await call_logger.log_call(
            session_id=session_id,
            user_message=req.message,
            reply=cached_reply,
            input_tokens=0,
            output_tokens=0,
            elapsed_ms=0,
            engine="cache",
            cache_hit=True,
        )
        return ChatResponse(
            reply=cached_reply,
            session_id=session_id,
            elapsed_ms=0,
            cache_hit=True,
        )

    # ── 2. 대화 이력 조회 ─────────────────────────────────
    history = _sessions.get(session_id, [])

    # ── 3. 메시지 조립 ────────────────────────────────────
    system_prompt = get_system_prompt(ipo_context=req.ipo_context)
    messages = (
        [{"role": "system", "content": system_prompt}]
        + history[-_MAX_HISTORY_TURNS * 2:]   # user/assistant 쌍이므로 *2
        + [{"role": "user", "content": req.message}]
    )

    # ── 4. LLM 호출 ───────────────────────────────────────
    try:
        result = await call_llm(messages)
    except NotImplementedError as e:
        raise HTTPException(status_code=501, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"LLM 호출 실패: {e}")

    reply = result["text"]

    # ── 5. 대화 이력 업데이트 ─────────────────────────────
    history.append({"role": "user", "content": req.message})
    history.append({"role": "assistant", "content": reply})
    _sessions[session_id] = history

    # ── 6. 캐시 저장 + 호출 로그 ─────────────────────────
    cache.set(req.message, reply)
    await call_logger.log_call(
        session_id=session_id,
        user_message=req.message,
        reply=reply,
        input_tokens=result["input_tokens"],
        output_tokens=result["output_tokens"],
        elapsed_ms=result["elapsed_ms"],
        engine=result["engine"],
        cache_hit=False,
    )

    return ChatResponse(
        reply=reply,
        session_id=session_id,
        elapsed_ms=result["elapsed_ms"],
        cache_hit=False,
    )
