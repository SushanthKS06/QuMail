import os
import secrets
from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )
    
    app_name: str = "QuMail Backend"
    app_version: str = "1.0.0"
    debug: bool = False
    
    host: str = "127.0.0.1"
    port: int = 8000
    
    secret_key: str = Field(default_factory=lambda: secrets.token_hex(32))
    api_token: str = "change_this_to_another_random_string"
    token_expire_minutes: int = 1440
    
    km_url: str = "http://127.0.0.1:8200"
    km_token: str = Field(default_factory=lambda: secrets.token_urlsafe(32))
    km_timeout: int = 60
    
    default_security_level: int = 2
    
    gmail_client_id: str = ""
    gmail_client_secret: str = ""
    gmail_redirect_uri: str = "http://127.0.0.1:8000/api/v1/auth/oauth/gmail/callback"
    
    yahoo_client_id: str = ""
    yahoo_client_secret: str = ""
    yahoo_redirect_uri: str = "http://127.0.0.1:8000/api/v1/auth/oauth/yahoo/callback"
    
    # SMTP Configuration (defaults to Gmail for backward compatibility)
    smtp_host: str = "smtp.gmail.com"
    smtp_port: int = 587
    smtp_from_email: str = "" # Optional override
    
    frontend_url: str = "http://localhost:5174"
    
    data_dir: Path = Field(default_factory=lambda: Path("./data"))
    db_encryption_key: str = Field(default_factory=lambda: secrets.token_hex(32))
    
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = "INFO"
    
    @field_validator("data_dir", mode="after")
    @classmethod
    def ensure_data_dir_exists(cls, v: Path) -> Path:
        v.mkdir(parents=True, exist_ok=True)
        return v
    
    @property
    def db_path(self) -> Path:
        return self.data_dir / "qumail.db"
    
    @property
    def key_cache_path(self) -> Path:
        return self.data_dir / "key_cache.enc"


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
