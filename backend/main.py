"""
QuMail Backend - Main Application Entry Point

This is the security core of QuMail. All cryptographic operations,
key management, and email protocol handling occurs here.

Security Notes:
- Binds to 127.0.0.1 only (no external access)
- All endpoints require bearer token authentication
- Keys never touch disk unencrypted
"""

import logging
import sys
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api import auth, emails, security, accounts
from api.dependencies import verify_startup_requirements
from config import settings
from storage.database import init_database

logging.basicConfig(
    level=getattr(logging, settings.log_level),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler for startup/shutdown."""
    logger.info("Starting QuMail Backend v%s", settings.app_version)
    logger.info("Binding to %s:%d (localhost only)", settings.host, settings.port)
    
    await init_database()
    logger.info("Database initialized at %s", settings.db_path)
    
    await verify_startup_requirements()
    logger.info("Startup requirements verified")
    
    yield
    
    logger.info("Shutting down QuMail Backend")


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="Quantum Secure Email Client Backend API",
    docs_url="/docs" if settings.debug else None,
    redoc_url="/redoc" if settings.debug else None,
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix="/api/v1/auth", tags=["Authentication"])
app.include_router(emails.router, prefix="/api/v1/emails", tags=["Emails"])
app.include_router(security.router, prefix="/api/v1/security", tags=["Security"])
app.include_router(accounts.router, prefix="/api/v1/accounts", tags=["Accounts"])


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "version": settings.app_version,
        "km_url": settings.km_url,
    }


if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
        log_level=settings.log_level.lower(),
    )
