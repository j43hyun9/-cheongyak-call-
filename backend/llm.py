import time
from openai import AsyncOpenAI
from backend.config import settings

_client: AsyncOpenAI | None = None


def _get_client() -> AsyncOpenAI:
    global _client
    if _client is None:
        _client = AsyncOpenAI(api_key=settings.openai_api_key)
    return _client


async def call_llm(messages: list[dict]) -> dict:
    """
    LLM 호출 → {text, input_tokens, output_tokens, elapsed_ms, engine}
    """
    engine = settings.llm_engine
    start = time.monotonic()

    if engine == "openai":
        response = await _get_client().chat.completions.create(
            model=settings.openai_model,
            messages=messages,
        )
        elapsed_ms = int((time.monotonic() - start) * 1000)
        return {
            "text": response.choices[0].message.content,
            "input_tokens": response.usage.prompt_tokens,
            "output_tokens": response.usage.completion_tokens,
            "elapsed_ms": elapsed_ms,
            "engine": settings.openai_model,
        }

    if engine == "perso":
        # TODO 전재형: PERSO API 계약 후 구현
        raise NotImplementedError("PERSO API 연동은 전재형이 API 계약 후 구현합니다.")

    if engine == "local":
        raise NotImplementedError("로컬 LLM 연동은 필요 시 구현합니다.")

    raise ValueError(f"알 수 없는 LLM 엔진: {engine!r}")
