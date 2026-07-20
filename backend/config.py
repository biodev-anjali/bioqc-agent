from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_ROOT = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    database_url: str = "sqlite:///./bioqc.db"
    upload_dir: Path = PROJECT_ROOT / "uploads"
    reports_dir: Path = PROJECT_ROOT / "reports"
    max_upload_size_mb: int = 100
    allowed_extensions: str = ".zip,.html,.gz,.tar.gz"
    cors_origins: str = "http://localhost:3000"
    api_prefix: str = "/api"
    gemini_api_key: str | None = None
    gemini_model: str = "gemini-3.5-flash"

    @property
    def max_upload_size_bytes(self) -> int:
        return self.max_upload_size_mb * 1024 * 1024

    @property
    def allowed_extension_set(self) -> set[str]:
        return {ext.strip().lower() for ext in self.allowed_extensions.split(",") if ext.strip()}

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
