"""
콜비(Colby) AI 백엔드 — 팀C 2차 프로젝트
실행: uvicorn backend.main:app --reload --port 8000
"""
import uuid
from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path
from typing import Literal

import edge_tts
from fastapi import FastAPI, File, Form, Query, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response
from fastapi.staticfiles import StaticFiles
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
from backend.preset_qa import lookup as preset_lookup
from backend.rag.colbi_rag import init_index, retrieve
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
    await init_index()  # FAISS 인덱스 1회 로드 (요청마다 재색인 금지)
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

# SadTalker 립싱크 영상 정적 파일 서빙
_SADTALKER_OUTPUT = Path(__file__).parent.parent / "frontend" / "public" / "sadtalker_output"
_SADTALKER_OUTPUT.mkdir(parents=True, exist_ok=True)
app.mount("/sadtalker_output", StaticFiles(directory=str(_SADTALKER_OUTPUT)), name="sadtalker_output")


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
    sources: list[dict]  # RAG(backend/rag) 검색 결과. {title,snippet,type,url}, 검색 결과 없으면 []
    usage: UsageOut
    latency_ms: int


@app.post("/chat", response_model=ChatResp, tags=["chat"])
async def chat(req: ChatReq):
    if not req.message.strip():
        return err("EMPTY_MESSAGE", "message가 비어 있습니다.")

    session_id = req.session_id or str(uuid.uuid4())

    # 1-a. 사전 정의 답변 확인 (LLM 호출 없이 즉시 반환, TTL 없음)
    preset = preset_lookup(req.message)
    if preset:
        await log_call(
            session_id=session_id, user_message=req.message, reply=preset,
            input_tokens=0, output_tokens=0, elapsed_ms=0,
            engine="preset", cache_hit=True, cost_usd=0.0,
        )
        return ChatResp(
            answer_text=preset, audio_url=None, state="speaking", sources=[],
            usage=UsageOut(model="preset", input_tokens=0, output_tokens=0, cost_usd=0.0),
            latency_ms=0,
        )

    # 1-b. 응답 캐시 확인
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

    # 2. RAG 검색 (backend/rag, 장두호) — 검색만 하고 LLM은 호출하지 않음
    ipo_context, sources = retrieve(req.message)

    # 3. 메시지 조립 (persona.colbi)
    # local 엔진(파인튜닝 모델)은 어투를 학습했으므로 few-shot 제외해 토큰 절약
    history = await load_history(session_id)
    messages = build_messages(
        history, req.message, ipo_context=ipo_context, slim=(settings.llm_engine == "local")
    )

    # 4. LLM 호출
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

    # 5. 세션 이력 업데이트
    await save_message(session_id, "user", req.message)
    await save_message(session_id, "assistant", reply)

    # 6. 캐시 저장 + 호출 로그
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
        sources=sources,
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

def _clean_for_tts(text: str) -> str:
    import re
    # 이모지/기호 제거 (ZWJ=‍, variation=️, keycap=⃣ 포함)
    text = re.sub(
        '[\U0001F000-\U0001FFFF\U00002500-\U00002BFF‍️⃣]+',
        '', text
    )
    # 마크다운 굵게/기울임/취소선
    text = re.sub(r'\*{1,3}|_{1,3}|~~', '', text)
    # 마크다운 헤더
    text = re.sub(r'^#+\s*', '', text, flags=re.MULTILINE)
    # 코드블록/인라인 코드
    text = re.sub(r'```[\s\S]*?```|`[^`]*`', '', text)
    # 마크다운 링크 → 텍스트만
    text = re.sub(r'!?\[([^\]]*)\]\([^\)]*\)', r'\1', text)
    # 마크다운 인용/테이블
    text = re.sub(r'^[>|]\s*', '', text, flags=re.MULTILINE)
    # 불릿 기호
    text = re.sub(r'^[-•·]\s+', '', text, flags=re.MULTILINE)
    # TTS가 이상하게 읽는 특수문자
    text = re.sub(r'[/\\~@#^&<>|%{}=+]', ' ', text)
    # 연속 공백/줄바꿈 정리
    text = re.sub(r'\n{2,}', ' ', text)
    text = re.sub(r'\s{2,}', ' ', text)
    return text.strip()

def _expand_to_syllables(text: str, offset_ms: int, duration_ms: int) -> list:
    # 완성형 한글 음절만 추출 (0xAC00~0xD7A3)
    syllables = [c for c in text if '가' <= c <= '힣']
    if not syllables:
        return [{"offsetMs": offset_ms, "text": text}]
    ms_per = duration_ms / len(syllables)
    return [
        {"offsetMs": int(offset_ms + i * ms_per), "text": syl}
        for i, syl in enumerate(syllables)
    ]

async def _generate_audio(text: str):
    import base64
    text = _clean_for_tts(text)
    communicate = edge_tts.Communicate(text, "ko-KR-HyunsuMultilingualNeural", pitch="+20Hz")
    audio_bytes = bytearray()
    boundaries = []
    async for chunk in communicate.stream():
        if chunk["type"] == "audio":
            audio_bytes.extend(chunk["data"])
        elif chunk["type"] in ("WordBoundary", "SentenceBoundary"):
            # offset/duration 단위: 100-nanosecond → ms
            offset_ms   = chunk["offset"]   // 10000
            duration_ms = chunk.get("duration", 0) // 10000
            # 어절 → 음절 단위로 쪼개서 각 음절에 타임스탬프 배분
            boundaries.extend(_expand_to_syllables(chunk["text"], offset_ms, duration_ms))
    return base64.b64encode(bytes(audio_bytes)).decode(), boundaries

@app.post("/tts", tags=["tts"])
async def tts_endpoint(request: TTSRequest):
    audio_b64, word_boundary = await _generate_audio(request.text)
    return {"audio": audio_b64, "word_boundary": word_boundary}


@app.post("/tts/video", tags=["tts"])
async def tts_video_endpoint(request: TTSRequest):
    """TTS 오디오 + HeyGen 립싱크 영상 생성. video_url이 None이면 생성 실패."""
    import base64
    from backend.heygen import generate_lipsync

    audio_b64, word_boundary = await _generate_audio(request.text)
    audio_bytes = base64.b64decode(audio_b64)

    video_url = await generate_lipsync(audio_bytes)
    return {
        "audio": audio_b64,
        "word_boundary": word_boundary,
        "video_url": video_url,
    }