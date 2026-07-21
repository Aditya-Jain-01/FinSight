from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str
    google_api_key: str
    gemini_model: str = "gemini-3.5-flash"  
    cors_origins: list[str] = [
        "http://localhost:3000",
        "https://finsight-f55scv9lk-adityajain7774-8470s-projects.vercel.app"
    ]

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()