"""Environment-overridable settings for sb-todos."""

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="SB_TODOS_", extra="ignore")

    db_path: Path = Path.home() / ".local" / "share" / "sb" / "todos.db"
    host: str = "127.0.0.1"
    port: int = 8788
    cors_origin: str = "http://localhost:5173"


settings = Settings()
