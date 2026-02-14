"""Configuration settings for jarvis-settings-server."""

import os
from functools import lru_cache


class Settings:
    """Application settings loaded from environment variables."""

    # Server settings
    PORT: int = int(os.getenv("PORT", "8014"))
    HOST: str = os.getenv("HOST", "0.0.0.0")

    # jarvis-config-service URL for service discovery
    JARVIS_CONFIG_URL: str = os.getenv("JARVIS_CONFIG_URL", "http://localhost:8013")

    # JWT settings - must match jarvis-auth
    JARVIS_AUTH_SECRET_KEY: str = os.getenv("JARVIS_AUTH_SECRET_KEY", "")
    JARVIS_AUTH_ALGORITHM: str = os.getenv("JARVIS_AUTH_ALGORITHM", "HS256")

    # HTTP client timeout for service calls (in seconds)
    SERVICE_TIMEOUT: float = float(os.getenv("SERVICE_TIMEOUT", "10.0"))


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
