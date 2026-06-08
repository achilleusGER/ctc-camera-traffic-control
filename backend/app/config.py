"""Backend-Settings: liest .env, validiert URLs, stellt Singletons bereit."""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ─── Datenbank ──────────────────────────────────────────────────────────
    postgres_user: str = "traffic"
    postgres_password: str = "traffic"
    postgres_db: str = "traffic"
    postgres_host: str = "127.0.0.1"
    postgres_port: int = 5432

    database_url: str = Field(
        default="postgresql+asyncpg://traffic:traffic@127.0.0.1:5432/traffic"
    )
    database_url_sync: str = Field(
        default="postgresql://traffic:traffic@127.0.0.1:5432/traffic"
    )

    # ─── Redis ──────────────────────────────────────────────────────────────
    redis_url: str = "redis://127.0.0.1:6379/0"

    # ─── Media / Beweis-Storage ─────────────────────────────────────────────
    media_backend: str = "local"  # aktuell nur "local"
    media_dir: Path = Path("/var/lib/trafficcontrol/media")

    # ─── Backend-Server ─────────────────────────────────────────────────────
    backend_host: str = "0.0.0.0"
    backend_port: int = 7890
    backend_cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"

    # ─── Streaming / WebSocket ──────────────────────────────────────────────
    # Token-Listen für Camera-Stream-Authorization (LAN-only, in Phase 6 erweitern)
    ws_heartbeat_seconds: int = 30

    # ─── Retention / Admin ──────────────────────────────────────────────────
    cleanup_min_age_days: int = 7  # Hard floor: nichts jünger als 7 Tage löschen

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.backend_cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    """Singleton: .env wird genau einmal gelesen."""
    return Settings()


# Convenience-Singleton
settings = get_settings()
