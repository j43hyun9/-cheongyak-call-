import time
from openai import AsyncOpenAI
from core.config import settings

_openai_client: AsyncOpenAI | None = None


def _get_openai_client() -> AsyncOpenAI:
    global _openai_client
    if _openai_client is None:
        _openai_client = AsyncOpenAI(api_key=settings.openai_api_key)
    return _openai_client


async def call_llm(messages: list[dict]) -> dict:
    """
    LLM을 호출하고 응답 + 사용량 통계를 반환합니다.

    Returns:
        {
            "text":          str   — 모델 응답 텍스트
            "input_tokens":  int   — 입력 토큰 수
            "output_tokens": int   — 출력 토큰 수
            "elapsed_ms":    int   — 응답 시간 (밀리초)
            "engine":        str   — 실제 사용한 모델 이름
        }
    """
    engine = settings.llm_engine
    start = time.monotonic()

    if engine == "openai":
        client = _get_openai_client()
        response = await client.chat.completions.create(
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
        # PERSO API — 전재형이 API 계약 완료 후 구현
        # 참고: https://perso.ai/
        raise NotImplementedError(
            "PERSO API 연동은 전재형이 API 계약 후 여기에 구현합니다."
        )

    if engine == "local":
        # Ollama 등 로컬 LLM — 필요 시 구현
        raise NotImplementedError("로컬 LLM 연동은 필요 시 구현합니다.")

    raise ValueError(f"알 수 없는 LLM 엔진: {engine!r}")
