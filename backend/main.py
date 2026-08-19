"""
콜비(Colby) AI 백엔드 — 팀C 2차 프로젝트
실행: uvicorn backend.main:app --reload --port 8000
"""
import uuid
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Literal

import edge_tts
from fastapi import FastAPI, File, Form, Query, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response
from pydantic import BaseModel

from backend import cache
from backend.config import settings
from backend.db import (
    create_schedule,
    delete_schedule,
    get_call_summary,
    get_schedules,
    init_db,
    load_history,
    log_call,
    save_message,
    update_schedule,
)
from backend.ipo_crawler import fetch_all_ipo, filter_ipo
from backend.llm import call_llm
from backend.persona.colbi import build_messages
from backend.stt import is_supported_content_type, transcribe


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
    answer_text: str
    audio_url: str | None = None  # None until TTS(/tts) 연동(김준서)
    state: Literal["idle", "listening", "thinking", "speaking"] = "speaking"
    sources: list[dict]  # RAG 연동 전까지 []. 연동 후 {title,url,snippet} 형태(장두호)
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
            answer_text=cached, audio_url=None, state="speaking", sources=[],
            usage=UsageOut(model="cache", input_tokens=0, output_tokens=0, cost_usd=0.0),
            latency_ms=0,
        )

    # 2. 메시지 조립 (persona.colbi)
    # local 엔진(파인튜닝 모델)은 어투를 학습했으므로 few-shot 제외해 토큰 절약
    history = await load_history(session_id)
    messages = build_messages(history, req.message, slim=(settings.llm_engine == "local"))

    # 3. LLM 호출
    try:
        result = await call_llm(messages)
    except NotImplementedError as e:
        return err("NOT_IMPLEMENTED", str(e), 501)
    except Exception as e:
        return err("LLM_ERROR", f"LLM 호출 실패: {e}", 502)

    reply = result["text"]
    cost_usd = 0.0 if settings.llm_engine == "local" else round(
        _cost(result["input_tokens"], result["output_tokens"]), 8
    )

    # 4. 세션 이력 업데이트
    await save_message(session_id, "user", req.message)
    await save_message(session_id, "assistant", reply)

    # 5. 캐시 저장 + 호출 로그
    cache.set(req.message, reply)
    await log_call(
        session_id=session_id, user_message=req.message, reply=reply,
        input_tokens=result["input_tokens"], output_tokens=result["output_tokens"],
        elapsed_ms=result["elapsed_ms"], engine=result["engine"],
        cache_hit=False, cost_usd=cost_usd,
    )

    return ChatResp(
        answer_text=reply,
        audio_url=None,
        state="speaking",
        sources=[],
        usage=UsageOut(
            model=result["engine"],
            input_tokens=result["input_tokens"],
            output_tokens=result["output_tokens"],
            cost_usd=cost_usd,
        ),
        latency_ms=result["elapsed_ms"],
    )


# ── POST /stt ─────────────────────────────────────────────────

class STTResp(BaseModel):
    text: str


@app.post("/stt", response_model=STTResp, tags=["stt"])
async def stt(audio: UploadFile = File(...), session_id: str = Form("")):
    content = await audio.read()
    if not content:
        return err("STT_EMPTY_AUDIO", "오디오 파일이 비어 있습니다.")
    if not is_supported_content_type(audio.content_type):
        return err(
            "STT_UNSUPPORTED_FORMAT",
            f"지원하지 않는 오디오 형식입니다: {audio.content_type}",
        )

    try:
        result = await transcribe(audio.filename or "audio.webm", content)
    except Exception as e:
        return err("STT_FAILED", f"STT 처리 실패: {e}", 502)

    if session_id:
        await log_call(
            session_id=session_id, user_message=None, reply=result["text"],
            input_tokens=0, output_tokens=0, elapsed_ms=result["elapsed_ms"],
            engine=result["engine"], cache_hit=False, cost_usd=0.0,
        )

    return STTResp(text=result["text"])


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

# ── POST /tts ─────────────────────────────────────────────────

class TTSRequest(BaseModel):
    text: str

async def _generate_audio(text: str) -> bytes:
    communicate = edge_tts.Communicate(text, "ko-KR-SunHiNeural")
    audio_bytes = bytearray()
    async for chunk in communicate.stream():
        if chunk["type"] == "audio":
            audio_bytes.extend(chunk["data"])
    return bytes(audio_bytes)

@app.post("/tts", tags=["tts"])
async def tts_endpoint(request: TTSRequest):
    audio_bytes = await _generate_audio(request.text)
    return Response(content=audio_bytes, media_type="audio/mpeg")