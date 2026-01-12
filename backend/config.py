"""
QuMail Backend Configuration

Manages all configuration settings with environment variable support.
Security-critical settings are validated and never logged.
"""

import os
import secrets
from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings with environment variable support."""
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )
    
    # Application
    app_name: str = "QuMail Backend"
    app_version: str = "1.0.0"
    debug: bool = False
    
    # Server
    host: str = "127.0.0.1"
    port: int = 8000
    
    # Security
    secret_key: str = Field(default_factory=lambda: secrets.token_hex(32))
    api_token: str = Field(default_factory=lambda: secrets.token_urlsafe(32))
    token_expire_minutes: int = 1440
    
    # Key Manager
    km_url: str = "http://127.0.0.1:8100"
    km_token: str = Field(default_factory=lambda: secrets.token_urlsafe(32))
    km_timeout: int = 30
    
    # Email
    default_security_level: int = 2
    
    # Gmail OAuth2
    gmail_client_id: str = ""
    gmail_client_secret: str = ""
    gmail_redirect_uri: str = "http://127.0.0.1:8000/api/v1/auth/oauth/gmail/callback"
    
    # Storage
    data_dir: Path = Field(default_factory=lambda: Path("./data"))
    db_encryption_key: str = Field(default_factory=lambda: secrets.token_hex(32))
    
    # Logging
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = "INFO"
    
    @field_validator("data_dir", mode="after")
    @classmethod
    def ensure_data_dir_exists(cls, v: Path) -> Path:
        """Create data directory if it doesn't exist."""
        v.mkdir(parents=True, exist_ok=True)
        return v
    
    @field_validator("host")
    @classmethod
    def validate_localhost_only(cls, v: str) -> str:
        """Ensure backend only binds to localhost for security."""
        if v not in ("127.0.0.1", "localhost", "::1"):
            raise ValueError("Backend must bind to localhost only for security")
        return v
    
    @property
    def db_path(self) -> Path:
        """Path to the SQLite database."""
        return self.data_dir / "qumail.db"
    
    @property
    def key_cache_path(self) -> Path:
        """Path to the encrypted key cache."""
        return self.data_dir / "key_cache.enc"


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()


settings = get_settings()
