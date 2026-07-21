from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str
    google_api_key: str
    huggingface_api_key: str
    groq_api_key: str
    groq_model: str = "llama-3.3-70b-versatile"

    cors_origins: list[str] = [
        "http://localhost:3000",
        "http://localhost:3001",
        "https://finsight-mauve-eight.vercel.app"
    ]

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()