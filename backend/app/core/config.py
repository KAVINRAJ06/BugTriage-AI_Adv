from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

# Project root: triage/.env (single source for local + Docker)
_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
_ENV_FILE = _PROJECT_ROOT / ".env"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=_ENV_FILE if _ENV_FILE.is_file() else None,
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Secrets — must be set in .env (no defaults in code)
    secret_key: str = Field(min_length=32)
    smtp_password: str = ""
    groq_api_key: str = ""

    # Connection / credentials (from .env; non-secret defaults only for local dev ergonomics)
    mongodb_url: str = "mongodb://localhost:27017"
    mongodb_db: str = "triage"
    smtp_host: str = "localhost"
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_from: str = "noreply@bugtriage.app"
    smtp_start_tls: bool = True
    smtp_tls: bool = False

    # App behavior
    otp_expire_minutes: int = 10
    jwt_expire_minutes: int = 60
    cors_origins: str = "http://localhost:3000"
    dev_log_otp: bool = True
    groq_model: str = "llama-3.1-8b-instant"
    public_api_base: str = "http://127.0.0.1:8000"
    app_public_url: str = "http://127.0.0.1:5500"
    duplicate_likelihood_threshold: float = 0.92
    allow_public_register: bool = True
    admin_email: str = "admin@example.com"
    admin_password: str = "change-me-admin-password"

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def smtp_configured(self) -> bool:
        return bool(self.smtp_host and self.smtp_from)

    @property
    def groq_configured(self) -> bool:
        return bool(self.groq_api_key)


settings = Settings()
