from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str
    google_api_key: str
    huggingface_api_key: str
    groq_api_key: str
    openrouter_api_key: str
    finnhub_api_key: str = ""  # Optional — Phase 3 only, empty = disabled
    gemma_model: str = "gemma-4-31b-it"
    openrouter_model: str = "nvidia/nemotron-3-super-120b-a12b:free"
    groq_fallback_model: str = "llama-3.3-70b-versatile"

    cors_origins: list[str] = [
        "http://localhost:3000",
        "http://localhost:3001",
        "http://127.0.0.1:3000",
        "https://finsight-mauve-eight.vercel.app"
    ]

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()