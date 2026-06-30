from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    # LLM 엔진 스위치 — "openai" | "perso" | "local"
    llm_engine: str = "openai"

    # OpenAI
    openai_api_key: str = ""
    openai_model: str = "gpt-4o-mini"

    # PERSO (전재형이 API 계약 후 채움)
    perso_api_key: str = ""
    perso_model: str = ""

    # 비용 추정 (USD / 1K tokens)
    cost_per_1k_input: float = 0.00015
    cost_per_1k_output: float = 0.00060

    # 응답 캐시 TTL (초)
    cache_ttl_seconds: int = 3600


settings = Settings()
