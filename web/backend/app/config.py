import os
from functools import lru_cache

from pydantic_settings import BaseSettings

# Heroku sets DATABASE_URL and PORT without a prefix — map them to
# the UPLINK_-prefixed names that pydantic-settings expects.
if "DATABASE_URL" in os.environ and "UPLINK_DATABASE_URL" not in os.environ:
    _url = os.environ["DATABASE_URL"]
    if _url.startswith("postgres://"):
        _url = _url.replace("postgres://", "postgresql+asyncpg://", 1)
    elif _url.startswith("postgresql://"):
        _url = _url.replace("postgresql://", "postgresql+asyncpg://", 1)
    os.environ["UPLINK_DATABASE_URL"] = _url

if "PORT" in os.environ and "UPLINK_PORT" not in os.environ:
    os.environ["UPLINK_PORT"] = os.environ["PORT"]


class Settings(BaseSettings):
    DATABASE_URL: str = "sqlite+aiosqlite:///./uplink.db"
    JWT_SECRET: str = "dev-secret-change-in-production"
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_MINUTES: int = 1440
    TICK_RATE: float = 5.0
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    CORS_ORIGINS: list[str] = ["http://localhost:5173"]

    model_config = {"env_prefix": "UPLINK_"}


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
