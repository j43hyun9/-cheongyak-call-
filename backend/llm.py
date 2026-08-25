import re
import time
from openai import AsyncOpenAI
from backend.config import settings


def _strip_artifact(text: str) -> str:
    """colbi-qwen이 학습 데이터 포맷(📋 / 📅 블록)을 응답 뒤에 덧붙이는 현상 제거."""
    # 독립 줄의 📋 이 처음 등장하는 지점부터 끝까지 전부 제거
    cleaned = re.sub(r'\n+[ \t]*📋[ \t]*[\s\S]*$', '', text)
    return cleaned.rstrip()

_openai_client: AsyncOpenAI | None = None
_local_client: AsyncOpenAI | None = None


def _get_openai_client() -> AsyncOpenAI:
    global _openai_client
    if _openai_client is None:
        _openai_client = AsyncOpenAI(api_key=settings.openai_api_key)
    return _openai_client


def _get_local_client() -> AsyncOpenAI:
    """Ollama OpenAI-compatible 엔드포인트 클라이언트."""
    global _local_client
    if _local_client is None:
        _local_client = AsyncOpenAI(
            base_url=settings.ollama_base_url,
            api_key="ollama",  # Ollama는 키 불필요, 빈 값 허용 안 해 더미 사용
        )
    return _local_client


async def call_llm(messages: list[dict]) -> dict:
    """
    LLM 호출 → {text, input_tokens, output_tokens, elapsed_ms, engine}
    """
    engine = settings.llm_engine
    start = time.monotonic()

    if engine == "openai":
        response = await _get_openai_client().chat.completions.create(
            model=settings.openai_model,
            messages=messages,
        )
        elapsed_ms = int((time.monotonic() - start) * 1000)
        return {
            "text": _strip_artifact(response.choices[0].message.content),
            "input_tokens": response.usage.prompt_tokens,
            "output_tokens": response.usage.completion_tokens,
            "elapsed_ms": elapsed_ms,
            "engine": settings.openai_model,
        }

    if engine == "local":
        response = await _get_local_client().chat.completions.create(
            model=settings.ollama_model,
            messages=messages,
        )
        elapsed_ms = int((time.monotonic() - start) * 1000)
        usage = response.usage
        return {
            "text": _strip_artifact(response.choices[0].message.content),
            "input_tokens": usage.prompt_tokens if usage else 0,
            "output_tokens": usage.completion_tokens if usage else 0,
            "elapsed_ms": elapsed_ms,
            "engine": settings.ollama_model,
        }

    if engine == "perso":
        raise NotImplementedError("PERSO API 연동은 전재형이 API 계약 후 구현합니다.")

    raise ValueError(f"알 수 없는 LLM 엔진: {engine!r}")
