from functools import lru_cache
from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Nova Bot"
    api_prefix: str = "/api"
    debug: bool = False
    secret_key: str = "change-me"
    access_token_expire_minutes: int = 30
    refresh_token_expire_minutes: int = 10080
    algorithm: str = "HS256"
    database_url: str = "sqlite+aiosqlite:///./nova_bot.db"
    openai_api_key: str = ""
    gemini_api_key: str = ""
    openai_model: str = "gpt-4o-mini"
    default_temperature: float = 0.7
    default_max_tokens: int = 700
    cors_origins: str = "http://localhost:5173,http://localhost:3000"
    rate_limit_per_minute: int = 60
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", case_sensitive=False)

    @field_validator("cors_origins")
    @classmethod
    def normalize_origins(cls, value: str) -> str:
        return value.strip()


@lru_cache
def get_settings() -> Settings:
    return Settings()
