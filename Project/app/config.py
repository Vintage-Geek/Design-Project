# app/config.py
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict

# Project root – reliable on Windows, regardless of cwd
BASE_DIR = Path(__file__).parent.parent
ENV_PATH = BASE_DIR / ".env"


class Settings(BaseSettings):
    DB_URL: str = "postgresql://user:pass@localhost:5432/insurance_agent"
    ASYNC_DB_URL: str = "postgresql+asyncpg://user:pass@localhost:5432/insurance_agent"
    REDIS_URL: str = "redis://localhost:6379/0"

    # New pydantic-settings v2 syntax (correct and future-proof)
    model_config = SettingsConfigDict(
        env_file=ENV_PATH if ENV_PATH.exists() else None,
        env_file_encoding="utf-8",
        extra="ignore",
    )


# This line will only execute if validation succeeds
settings = Settings()