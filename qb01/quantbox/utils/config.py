"""Centralized configuration, loaded from environment variables.

Any configurable value, such as database credentials or the default exchange, must
go through this module rather than being hardcoded elsewhere in the project.
"""

from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Global settings for QB-01.

    Values can be overridden through a .env file at the root of qb01, or through real
    environment variables, which always take priority.
    """

    model_config = SettingsConfigDict(env_file=".env", env_prefix="QB_", extra="ignore")

    db_host: str = "localhost"
    db_port: int = 5432
    db_name: str = "quantbox"
    db_user: str = "quantbox"
    db_password: str = "quantbox_dev_password"

    default_exchange: str = "binance"

    log_level: str = "INFO"

    @property
    def database_url(self) -> str:
        """SQLAlchemy and psycopg connection URL for PostgreSQL."""
        return (
            f"postgresql+psycopg://{self.db_user}:{self.db_password}"
            f"@{self.db_host}:{self.db_port}/{self.db_name}"
        )


settings = Settings()
