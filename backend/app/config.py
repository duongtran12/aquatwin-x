from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


PROJECT_ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    aquatwin_runtime_mode: Literal["auto", "real", "demo"] = "auto"
    aquatwin_version: str = "1.0.0"
    aquatwin_build_commit: str = "development"
    aquatwin_cors_origins: str = "http://localhost:5173"

    model_config = SettingsConfigDict(
        env_file=PROJECT_ROOT / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @property
    def cors_origins(self) -> list[str]:
        origins = [item.strip().rstrip("/") for item in self.aquatwin_cors_origins.split(",")]
        return [item for item in origins if item]


@lru_cache
def get_settings() -> Settings:
    return Settings()
