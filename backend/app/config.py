from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str
    google_api_key: str
    huggingface_api_key: str
    groq_api_key: str
    groq_model: str = "openai/gpt-oss-120b"

    cors_origins: list[str] = [
        "http://localhost:3000",
        "http://localhost:3001",
        "https://finsight-f55scv9lk-adityajain7774-8470s-projects.vercel.app"
    ]

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()