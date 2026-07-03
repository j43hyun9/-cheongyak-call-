from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    llm_engine: str = "openai"
    openai_api_key: str = ""
    openai_model: str = "gpt-4o-mini"
    perso_api_key: str = ""
    perso_model: str = ""

    ollama_base_url: str = "http://localhost:11434/v1"
    ollama_model: str = "colbi-qwen"   # Ollama에 pull된 모델명 (파인튜닝 완료 후 설정)

    cost_per_1k_input: float = 0.00015   # gpt-4o-mini 기준
    cost_per_1k_output: float = 0.00060

    cache_ttl_seconds: int = 3600        # 응답 캐시 TTL (1h)


settings = Settings()
