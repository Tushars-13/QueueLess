"""Application configuration loaded from environment variables (.env)."""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Typed application settings.

    Values are read from environment variables and an optional ``.env`` file.
    See ``.env.example`` for the full list of supported settings.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # --- Application ---
    app_name: str = "QueueLess"
    app_env: str = "development"
    app_debug: bool = True
    app_version: str = "0.1.0"

    # --- Database ---
    database_host: str = "localhost"
    database_port: int = 5432
    database_user: str = "queueless"
    database_password: str = "queueless"
    database_name: str = "queueless"
    database_echo: bool = False

    # --- Pool ---
    database_pool_size: int = 10
    database_max_overflow: int = 20
    database_pool_timeout: int = 30

    # --- Authentication (JWT) ---
    jwt_secret_key: str = "change-me-queueless-dev-only-jwt-secret-key"
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 30

    @property
    def database_url(self) -> str:
        """Build the async (asyncpg) SQLAlchemy DSN from parts."""
        return (
            f"postgresql+asyncpg://{self.database_user}:{self.database_password}"
            f"@{self.database_host}:{self.database_port}/{self.database_name}"
        )


@lru_cache
def get_settings() -> Settings:
    """Return a cached Settings instance (parsed once per process)."""
    return Settings()
