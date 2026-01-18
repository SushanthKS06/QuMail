import logging
import sys
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api import auth, emails, security, accounts, settings
from api.dependencies import verify_startup_requirements
from config import settings as config_settings
from storage.database import init_database

logging.basicConfig(
    level=getattr(logging, config_settings.log_level),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting QuMail Backend v%s", config_settings.app_version)
    logger.info("Binding to %s:%d (localhost only)", config_settings.host, config_settings.port)
    
    await init_database()
    logger.info("Database initialized at %s", config_settings.db_path)
    
    await verify_startup_requirements()
    logger.info("Startup requirements verified")
    
    yield
    
    logger.info("Shutting down QuMail Backend")


app = FastAPI(
    title=config_settings.app_name,
    version=config_settings.app_version,
    description="Quantum Secure Email Client Backend API",
    docs_url="/docs" if config_settings.debug else None,
    redoc_url="/redoc" if config_settings.debug else None,
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
app.include_router(settings.router, prefix="/api/v1/settings", tags=["Settings"])


@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "version": config_settings.app_version,
        "km_url": config_settings.km_url,
    }


if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host=config_settings.host,
        port=config_settings.port,
        reload=config_settings.debug,
        log_level=config_settings.log_level.lower(),
    )
