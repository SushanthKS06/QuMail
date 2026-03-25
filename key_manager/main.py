import asyncio
import logging
import signal
import sys
import time
from collections import defaultdict
from contextlib import asynccontextmanager
from typing import Dict

import uvicorn
from fastapi import FastAPI, Request, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from starlette.responses import JSONResponse
from starlette.types import ASGIApp, Receive, Scope, Send

from api import keys, status as status_api
from config import settings
from core.key_pool import KeyPool

logging.basicConfig(
    level=logging.DEBUG if settings.debug else logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger(__name__)

key_pool: KeyPool = None


class RateLimitMiddleware:
    """Pure ASGI middleware to avoid BaseHTTPMiddleware deadlock issues."""
    
    def __init__(self, app: ASGIApp, requests_per_minute: int = 100):
        self.app = app
        self.requests_per_minute = requests_per_minute
        self.request_counts: Dict[str, list] = defaultdict(list)
    
    async def __call__(self, scope: Scope, receive: Receive, send: Send):
        if scope["type"] != "http" or not settings.rate_limit_enabled:
            await self.app(scope, receive, send)
            return
        
        client = scope.get("client")
        client_ip = client[0] if client else "unknown"
        current_time = time.time()
        
        # Clean old entries and check rate limit
        self.request_counts[client_ip] = [
            t for t in self.request_counts[client_ip]
            if current_time - t < 60
        ]
        
        if len(self.request_counts[client_ip]) >= self.requests_per_minute:
            response = JSONResponse(
                status_code=429,
                content={"detail": f"Rate limit exceeded. Max {self.requests_per_minute} requests per minute."}
            )
            await response(scope, receive, send)
            return
        
        self.request_counts[client_ip].append(current_time)
        await self.app(scope, receive, send)


async def cleanup_expired_keys():
    while True:
        try:
            await asyncio.sleep(300)
            if key_pool:
                count = key_pool.cleanup_expired()
                if count > 0:
                    logger.info("Cleaned up %d expired keys", count)
        except asyncio.CancelledError:
            break
        except Exception as e:
            logger.error("Error in cleanup task: %s", e)


cleanup_task = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global key_pool, cleanup_task
    
    logger.info("=" * 60)
    logger.info("QuMail Key Manager v%s (Production-Ready)", settings.app_version)
    logger.info("=" * 60)
    
    if settings.persistence_enabled:
        logger.info("Persistence: ENABLED (%s)", settings.persistence_path)
    else:
        logger.info("Persistence: DISABLED (in-memory only)")
    
    if settings.audit_enabled:
        logger.info("Audit Logging: ENABLED (%s)", settings.audit_path)
    
    if settings.rate_limit_enabled:
        logger.info("Rate Limiting: %d requests/minute", settings.rate_limit_per_minute)
    
    logger.info("Binding to %s:%d", settings.host, settings.port)
    
    key_pool = KeyPool(
        persistence_enabled=settings.persistence_enabled,
        persistence_path=settings.persistence_path if settings.persistence_enabled else None,
        persistence_password=settings.persistence_password if settings.persistence_enabled else None,
        audit_path=settings.audit_path if settings.audit_enabled else None,
    )
    
    # Run blocking initialization in thread executor to keep event loop responsive
    import asyncio
    loop = asyncio.get_event_loop()
    await loop.run_in_executor(
        None,
        key_pool.initialize,
        settings.initial_otp_pool_bytes,
        settings.initial_aes_keys,
    )
    
    stats = key_pool.get_stats()
    logger.info("Key pool status:")
    logger.info("  - OTP available: %d bytes", stats["otp_available"])
    logger.info("  - AES keys available: %d", stats["aes_available"])
    logger.info("  - Quantum entropy: %s", "YES" if stats.get("quantum_entropy") else "NO")
    
    
    # Initialize QKD Link for distributed synchronization
    from core.qkd_link import get_qkd_link
    qkd_link = get_qkd_link()
    
    # Register hook: When we create a key, push it to the peer via QKD Link
    async def sync_key_to_peer(peer_id, key_entry):
        await qkd_link.push_key(peer_id, key_entry)
        
    def sync_hook_wrapper(peer_id, key_entry):
        # Fire-and-forget async call from synchronous hook
        try:
            loop = asyncio.get_running_loop()
            loop.create_task(sync_key_to_peer(peer_id, key_entry))
        except RuntimeError:
            pass # No loop running
            
    key_pool.register_allocation_hook(sync_hook_wrapper)
    
    app.state.key_pool = key_pool
    
    cleanup_task = asyncio.create_task(cleanup_expired_keys())
    
    logger.info("Key Manager ready to accept connections")
    
    yield
    
    logger.info("Shutting down Key Manager...")
    
    if cleanup_task:
        cleanup_task.cancel()
        try:
            await cleanup_task
        except asyncio.CancelledError:
            pass
            
    await qkd_link.shutdown()
    
    if key_pool:
        key_pool.shutdown()
    
    logger.info("Key Manager shutdown complete")


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="Production-Ready Simulated QKD Key Manager with quantum-grade entropy",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://127.0.0.1:3000", "http://localhost:3000", "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "DELETE"],
    allow_headers=["*"],
)

app.add_middleware(RateLimitMiddleware, requests_per_minute=settings.rate_limit_per_minute)

app.include_router(status_api.router, prefix="/api/v1", tags=["Status"])
app.include_router(keys.router, prefix="/api/v1/keys", tags=["Keys"])


@app.get("/health")
async def health_check():
    stats = key_pool.get_stats() if key_pool else {}
    
    return {
        "status": "healthy",
        "version": settings.app_version,
        "production_ready": True,
        "features": {
            "quantum_entropy": stats.get("quantum_entropy", False),
            "persistence": settings.persistence_enabled,
            "audit_logging": settings.audit_enabled,
            "rate_limiting": settings.rate_limit_enabled,
        },
        "entropy_healthy": stats.get("entropy_healthy", True),
    }


@app.get("/api/v1/entropy/stats")
async def entropy_stats():
    try:
        from crypto_engine.secure_random import get_random_stats
        return get_random_stats()
    except ImportError:
        return {"error": "Quantum sim not available"}


def signal_handler(signum, frame):
    logger.info("Received signal %d, initiating shutdown...", signum)
    if key_pool:
        key_pool.shutdown()
    sys.exit(0)


if __name__ == "__main__":
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    ssl_config = {}
    if settings.ssl_cert_file and settings.ssl_key_file:
        import ssl
        ssl_config["ssl_keyfile"] = str(settings.ssl_key_file)
        ssl_config["ssl_certfile"] = str(settings.ssl_cert_file)
        if settings.ssl_ca_file:
            ssl_config["ssl_ca_certs"] = str(settings.ssl_ca_file)
            ssl_config["ssl_cert_reqs"] = ssl.CERT_REQUIRED # Enforce Client Auth
            logger.info("mTLS Enabled: Requiring valid client certificate")
        else:
            logger.warning("TLS Enabled but no CA file provided - Client Auth NOT enforced")

    uvicorn.run(
        "main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
        log_level="debug" if settings.debug else "info",
        **ssl_config,
    )
