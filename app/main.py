"""Main entry point for jarvis-settings-server.

Centralized settings aggregator that proxies settings requests to all
Jarvis microservices. Requires superuser JWT authentication.
"""

import logging
import os
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.routes import settings_router

# Set up logging
console_level = os.getenv("JARVIS_LOG_CONSOLE_LEVEL", "INFO")
logging.basicConfig(
    level=getattr(logging, console_level.upper(), logging.INFO),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("jarvis-settings-server")

_jarvis_handler = None


def _setup_remote_logging() -> None:
    """Set up remote logging to jarvis-logs server."""
    global _jarvis_handler
    try:
        from jarvis_log_client import init as init_log_client, JarvisLogHandler

        app_id = os.getenv("JARVIS_APP_ID", "jarvis-settings-server")
        app_key = os.getenv("JARVIS_APP_KEY")
        if not app_key:
            logger.debug("JARVIS_APP_KEY not set, skipping remote logging")
            return

        init_log_client(app_id=app_id, app_key=app_key)

        remote_level = os.getenv("JARVIS_LOG_REMOTE_LEVEL", "DEBUG")
        _jarvis_handler = JarvisLogHandler(
            service="jarvis-settings-server",
            level=getattr(logging, remote_level.upper(), logging.DEBUG),
        )

        for logger_name in ["uvicorn", "uvicorn.error", "uvicorn.access", "jarvis-settings-server"]:
            logging.getLogger(logger_name).addHandler(_jarvis_handler)

        logger.info("Remote logging enabled to jarvis-logs")
    except ImportError as exc:
        logger.debug("jarvis_log_client not available: %s", exc)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler."""
    # Startup
    _setup_remote_logging()
    settings = get_settings()
    logger.info(
        "jarvis-settings-server starting on %s:%d",
        settings.HOST,
        settings.PORT,
    )
    logger.info("Using config service at: %s", settings.JARVIS_CONFIG_URL)

    if not settings.JARVIS_AUTH_SECRET_KEY:
        logger.warning("JARVIS_AUTH_SECRET_KEY not configured - JWT validation will fail!")

    yield

    # Shutdown
    logger.info("jarvis-settings-server shutting down")


app = FastAPI(
    title="Jarvis Settings Server",
    description="Centralized settings aggregator for Jarvis microservices",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS - allow all origins for internal service communication.
# allow_credentials=False: endpoints use header auth (Bearer JWT), not cookies,
# and wildcard origins with credentials is invalid per the CORS spec.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routes
app.include_router(settings_router)


@app.get("/health")
def health() -> dict:
    """Health check endpoint."""
    return {"status": "ok", "service": "jarvis-settings-server"}


if __name__ == "__main__":
    settings = get_settings()
    uvicorn.run(app, host=settings.HOST, port=settings.PORT)
