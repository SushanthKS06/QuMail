import secrets
from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )
    
    app_name: str = "QuMail Key Manager"
    app_version: str = "1.0.0"
    debug: bool = True
    
    host: str = "127.0.0.1"
    port: int = 8100
    
    api_token: str = Field(default_factory=lambda: secrets.token_urlsafe(32))
    
    initial_otp_pool_bytes: int = 10 * 1024 * 1024
    initial_aes_keys: int = 1000
    max_key_size: int = 1024 * 1024
    
    key_ttl_seconds: int = 86400


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
