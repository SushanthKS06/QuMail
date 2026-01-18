import secrets
from functools import lru_cache
from pathlib import Path
from typing import Dict, Optional

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )
    
    app_name: str = "QuMail Key Manager"
    app_version: str = "2.0.0"
    debug: bool = False
    
    host: str = "127.0.0.1"
    port: int = 8100
    
    api_token: str = Field(default_factory=lambda: secrets.token_urlsafe(32))
    
    initial_otp_pool_bytes: int = 10 * 1024 * 1024
    initial_aes_keys: int = 1000
    max_key_size: int = 1024 * 1024
    
    key_ttl_seconds: int = 86400
    
    persistence_enabled: bool = True
    persistence_path: Path = Field(default_factory=lambda: Path("./data/keystore.enc"))
    persistence_password: str = Field(default_factory=lambda: secrets.token_urlsafe(32))
    
    audit_enabled: bool = True
    audit_path: Path = Field(default_factory=lambda: Path("./data/audit.log"))
    
    rate_limit_enabled: bool = True
    rate_limit_per_minute: int = 100
    
    multi_user_enabled: bool = True
    default_quota_otp_bytes: int = 1024 * 1024
    default_quota_aes_keys: int = 100
    
    # Distributed QKD Simulation
    local_peer_id: str = "km-local"
    peers: Dict[str, str] = {}  # Format: {"km-remote": "http://remote-ip:8100"}
    qkd_link_secret: str = Field(default_factory=lambda: secrets.token_urlsafe(32))

    # mTLS Security
    ssl_ca_file: Optional[Path] = Field(default=None) # Path to CA cert to verify clients
    ssl_cert_file: Optional[Path] = Field(default=None) # Path to this node's cert
    ssl_key_file: Optional[Path] = Field(default=None) # Path to this node's key


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
