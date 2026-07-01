"""
콜비(Colby) AI 백엔드 — 팀C 2차 프로젝트
실행: uvicorn backend.main:app --reload --port 8000
"""
import uuid
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Literal

from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from backend import cache
from backend.config import settings
from backend.db import (
    create_schedule,
    delete_schedule,
    get_call_summary,
    get_schedules,
    init_db,
    log_call,
    update_schedule,
)
from backend.ipo_crawler import fetch_all_ipo, filter_ipo
from backend.llm import call_llm
from backend.persona.colbi import build_messages

# ── 세션 (in-memory) — TODO 김준서: SQLite conversation 테이블로 이전 ──
_sessions: dict[str, list[dict]] = {}

_IPO_KW = {
    "공모주", "청약", "공모", "ipo", "상장", "주관사", "주간사",
    "이번주", "다음주", "이번 주", "다음 주", "오늘 청약",
}


def _is_ipo_question(msg: str) -> bool:
    low = msg.lower()
    return any(kw in low for kw in _IPO_KW)


def _items_to_context(items: list[dict]) -> str:
    return "\n".join(
        f"- {it['name']}: 청약기간 {it['start']}~{it['end']}, "
        f"공모가 {it['price']}원, 주관사 {it['underwriter']}"
        for it in items
    )


def _cost(input_tokens: int, output_tokens: int) -> float:
    return (
        input_tokens * settings.cost_per_1k_input / 1000
        + output_tokens * settings.cost_per_1k_output / 1000
    )


def err(code: str, message: str, status: int = 400) -> JSONResponse:
    return JSONResponse(
        status_code=status,
        content={"error": {"code": code, "message": message}},
    )


# ── lifespan ──────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    yield


app = FastAPI(
    title="콜비(Colby) AI 백엔드",
    description="공모주 투자 길잡이 콜비 — 팀C 2차 프로젝트",
    version="0.2.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── /health ───────────────────────────────────────────────────

@app.get("/health", tags=["util"])
async def health():
    return {"status": "ok"}


# ── POST /chat ────────────────────────────────────────────────

class ChatReq(BaseModel):
    session_id: str = ""
    message: str


class UsageOut(BaseModel):
    model: str
    input_tokens: int
    output_tokens: int
    cost_usd: float


class ChatResp(BaseModel):
    reply: str
    sources: list[dict]
    usage: UsageOut
    latency_ms: int


@app.post("/chat", response_model=ChatResp, tags=["chat"])
async def chat(req: ChatReq):
    if not req.message.strip():
        return err("EMPTY_MESSAGE", "message가 비어 있습니다.")

    session_id = req.session_id or str(uuid.uuid4())

    # 1. 응답 캐시 확인
    cached = cache.get(req.message)
    if cached:
        await log_call(
            session_id=session_id, user_message=req.message, reply=cached,
            input_tokens=0, output_tokens=0, elapsed_ms=0,
            engine="cache", cache_hit=True, cost_usd=0.0,
        )
        return ChatResp(
            reply=cached, sources=[],
            usage=UsageOut(model="cache", input_tokens=0, output_tokens=0, cost_usd=0.0),
            latency_ms=0,
        )

    # 2. 공모주 RAG — 일정 관련 질문이면 크롤러 결과 주입
    sources: list[dict] = []
    ipo_context = ""
    if _is_ipo_question(req.message):
        all_ipo = await fetch_all_ipo()
        if all_ipo:
            sources = all_ipo
            ipo_context = _items_to_context(all_ipo)

    # 3. 메시지 조립 (persona.colbi)
    history = _sessions.get(session_id, [])
    messages = build_messages(history, req.message, ipo_context)

    # 4. LLM 호출
    try:
        result = await call_llm(messages)
    except NotImplementedError as e:
        return err("NOT_IMPLEMENTED", str(e), 501)
    except Exception as e:
        return err("LLM_ERROR", f"LLM 호출 실패: {e}", 502)

    reply = result["text"]
    cost_usd = round(_cost(result["input_tokens"], result["output_tokens"]), 8)

    # 5. 세션 이력 업데이트
    history.append({"role": "user", "content": req.message})
    history.append({"role": "assistant", "content": reply})
    _sessions[session_id] = history

    # 6. 캐시 저장 + 호출 로그
    cache.set(req.message, reply)
    await log_call(
        session_id=session_id, user_message=req.message, reply=reply,
        input_tokens=result["input_tokens"], output_tokens=result["output_tokens"],
        elapsed_ms=result["elapsed_ms"], engine=result["engine"],
        cache_hit=False, cost_usd=cost_usd,
    )

    return ChatResp(
        reply=reply,
        sources=sources,
        usage=UsageOut(
            model=result["engine"],
            input_tokens=result["input_tokens"],
            output_tokens=result["output_tokens"],
            cost_usd=cost_usd,
        ),
        latency_ms=result["elapsed_ms"],
    )


# ── GET /ipo/schedule ─────────────────────────────────────────

@app.get("/ipo/schedule", tags=["ipo"])
async def ipo_schedule(
    range: Literal["today", "this_week", "next_week", "all"] = Query("all"),
):
    all_items = await fetch_all_ipo()
    items = filter_ipo(all_items, range)
    return {
        "today": datetime.today().strftime("%Y-%m-%d"),
        "count": len(items),
        "items": items,
    }


# ── /schedules CRUD ───────────────────────────────────────────

class ScheduleCreate(BaseModel):
    title: str
    datetime: str


class ScheduleUpdate(BaseModel):
    title: str | None = None
    datetime: str | None = None


@app.post("/schedules", status_code=201, tags=["schedules"])
async def schedule_create(body: ScheduleCreate):
    return await create_schedule(body.title, body.datetime)


@app.get("/schedules", tags=["schedules"])
async def schedule_list(date: str | None = Query(None)):
    return await get_schedules(date)


@app.put("/schedules/{id}", tags=["schedules"])
async def schedule_update(id: int, body: ScheduleUpdate):
    result = await update_schedule(id, body.title, body.datetime)
    if result is None:
        return err("NOT_FOUND", f"스케줄 {id}를 찾을 수 없습니다.", 404)
    return result


@app.delete("/schedules/{id}", tags=["schedules"])
async def schedule_delete(id: int):
    ok = await delete_schedule(id)
    if not ok:
        return err("NOT_FOUND", f"스케줄 {id}를 찾을 수 없습니다.", 404)
    return {"ok": True}


# ── GET /logs/summary ─────────────────────────────────────────

@app.get("/logs/summary", tags=["util"])
async def logs_summary():
    summary = await get_call_summary()
    summary["cache"] = cache.stats()
    return summary
