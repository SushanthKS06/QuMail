"""
Simulated QKD Key Manager

This is a SIMULATION of a QKD Key Manager following ETSI GS QKD 014.
In production, this would interface with actual QKD hardware.

The KM provides:
- Pre-provisioned symmetric key material
- Key allocation and lifecycle management
- One-time key consumption enforcement
- Status reporting

⚠️ SIMULATION NOTICE ⚠️
This uses cryptographically secure random numbers (CSPRNG) to
simulate QKD output. Real QKD uses quantum physics for true randomness.
For demonstration and testing purposes only.
"""

import logging
import sys
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api import keys, status
from config import settings
from core.key_pool import KeyPool

logging.basicConfig(
    level=logging.DEBUG if settings.debug else logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger(__name__)

key_pool: KeyPool = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler."""
    global key_pool
    
    logger.info("=" * 60)
    logger.info("Starting Simulated QKD Key Manager v%s", settings.app_version)
    logger.info("=" * 60)
    logger.warning("⚠️  SIMULATION MODE - Not real QKD hardware")
    logger.info("Binding to %s:%d", settings.host, settings.port)
    
    key_pool = KeyPool()
    key_pool.initialize(
        otp_bytes=settings.initial_otp_pool_bytes,
        aes_keys=settings.initial_aes_keys,
    )
    
    logger.info("Key pool initialized:")
    logger.info("  - OTP pool: %d bytes", settings.initial_otp_pool_bytes)
    logger.info("  - AES keys: %d", settings.initial_aes_keys)
    
    app.state.key_pool = key_pool
    
    yield
    
    logger.info("Shutting down Key Manager")


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="Simulated ETSI GS QKD 014 Key Manager",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(keys.router, prefix="/api/v1/keys", tags=["Keys"])
app.include_router(status.router, prefix="/api/v1", tags=["Status"])


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "version": settings.app_version,
        "simulation": True,
    }


if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
        log_level="debug" if settings.debug else "info",
    )
