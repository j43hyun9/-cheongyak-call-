import time
from openai import AsyncOpenAI
from backend.config import settings

_openai_client: AsyncOpenAI | None = None

# 1차 stt.py에서 이식 — 공모주 도메인 환각 방지용 힌트
DOMAIN_PROMPT = "공모주, 청약, 등록, 일정, 회의 관련 명령입니다."

SUPPORTED_CONTENT_TYPES = {
    "audio/webm", "audio/wav", "audio/wave", "audio/x-wav",
    "audio/mpeg", "audio/mp3", "audio/mp4", "audio/m4a", "audio/ogg",
}


def is_supported_content_type(content_type: str | None) -> bool:
    if not content_type:
        return False
    return content_type.split(";")[0].strip().lower() in SUPPORTED_CONTENT_TYPES


def _get_openai_client() -> AsyncOpenAI:
    global _openai_client
    if _openai_client is None:
        _openai_client = AsyncOpenAI(api_key=settings.openai_api_key)
    return _openai_client


async def transcribe(filename: str, content: bytes) -> dict:
    """
    오디오 바이트 → {text, elapsed_ms, engine}
    """
    engine = settings.stt_engine
    start = time.monotonic()

    if engine == "openai":
        response = await _get_openai_client().audio.transcriptions.create(
            model=settings.stt_model,
            file=(filename, content),
            language="ko",
            prompt=DOMAIN_PROMPT,
        )
        elapsed_ms = int((time.monotonic() - start) * 1000)
        return {
            "text": response.text.strip(),
            "elapsed_ms": elapsed_ms,
            "engine": settings.stt_model,
        }

    raise ValueError(f"알 수 없는 STT 엔진: {engine!r}")
