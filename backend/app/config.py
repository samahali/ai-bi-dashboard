from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import field_validator, Field
from typing import Literal
import secrets


class Settings(BaseSettings):
    """
    Application settings loaded from environment variables.
    Uses Pydantic v2 BaseSettings for validation and type safety.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
        json_schema_extra={"env_nested_delimiter": ","},
    )

    # ──────────────────────────────────────────
    # Application
    # ──────────────────────────────────────────
    app_name: str = "AI BI Dashboard"
    app_env: Literal["development", "production", "test"] = "development"
    debug: bool = False
    log_level: str = "INFO"
    api_prefix: str = "/api/v1"

    # ──────────────────────────────────────────
    # Security / JWT
    # ──────────────────────────────────────────
    secret_key: str = secrets.token_urlsafe(64)
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 60
    refresh_token_expire_days: int = 7

    # Auth cookies. Tokens are delivered as httpOnly cookies so client-side
    # JavaScript (and therefore any XSS) can't read them. `secure` is forced
    # on in production (requires HTTPS); `samesite=lax` blocks the token
    # cookie from being sent on cross-site requests, which covers the common
    # CSRF vectors for this same-origin app. `cookie_domain` left None so the
    # browser scopes it to the serving host.
    cookie_secure: bool = False          # overridden to True in production, see is_production
    cookie_samesite: str = "lax"         # lax | strict | none
    cookie_domain: str | None = None

    # ──────────────────────────────────────────
    # CORS
    # ──────────────────────────────────────────
    allowed_origins: str = "http://localhost:3000,http://localhost:5173"

    # ──────────────────────────────────────────
    # Database
    # ──────────────────────────────────────────
    database_url: str = "postgresql://bidashboard:bidashboard_secret@postgres:5432/bi_dashboard"

    # ──────────────────────────────────────────
    # ChromaDB
    # ──────────────────────────────────────────
    chromadb_host: str = "chromadb"
    chromadb_port: int = 8000

    # ──────────────────────────────────────────
    # LLM Providers
    # ──────────────────────────────────────────
    default_llm_provider: Literal["granite", "openai"] = "granite"

    # IBM Watsonx
    watsonx_apikey: str = ""
    watsonx_url: str = "https://us-south.ml.cloud.ibm.com"
    watsonx_project_id: str = ""
    watsonx_model_id: str = "ibm/granite-13b-instruct-v2"

    # OpenAI
    openai_api_key: str = ""
    openai_model: str = "gpt-4-turbo"

    # ──────────────────────────────────────────
    # File Storage
    # ──────────────────────────────────────────
    upload_dir: str = "/app/storage/uploads"
    reports_dir: str = "/app/storage/reports"
    max_upload_size_mb: int = 100
    allowed_file_types: str = "csv,xlsx,json"

    # ──────────────────────────────────────────
    # Rate Limiting
    # ──────────────────────────────────────────
    rate_limit_per_minute: int = 60
    rate_limit_per_hour: int = 500

    @property
    def max_upload_size_bytes(self) -> int:
        return self.max_upload_size_mb * 1024 * 1024

    @property
    def is_development(self) -> bool:
        return self.app_env == "development"

    @property
    def is_production(self) -> bool:
        return self.app_env == "production"

    @property
    def allowed_origins_list(self) -> list[str]:
        return [origin.strip() for origin in self.allowed_origins.split(",") if origin.strip()]

    @property
    def allowed_file_types_list(self) -> list[str]:
        return [ft.strip().lower() for ft in self.allowed_file_types.split(",") if ft.strip()]


# Single global instance — import this everywhere
settings = Settings()
