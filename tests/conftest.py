"""Test configuration and fixtures for jarvis-settings-server."""

import os
from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient
from jose import jwt

# Set environment before imports
os.environ["JARVIS_AUTH_SECRET_KEY"] = "test-secret-key-for-settings-server"
os.environ["JARVIS_AUTH_ALGORITHM"] = "HS256"
os.environ["JARVIS_CONFIG_URL"] = "http://localhost:8013"
os.environ["SERVICE_TIMEOUT"] = "5.0"

from app.main import app
from app.config import get_settings


@pytest.fixture
def settings():
    """Get application settings."""
    return get_settings()


@pytest.fixture
def client():
    """Create test client."""
    return TestClient(app)


def create_test_jwt(
    user_id: int = 1,
    email: str = "test@example.com",
    is_superuser: bool = False,
    expired: bool = False,
) -> str:
    """Create a test JWT token.

    Args:
        user_id: User ID to include in the token
        email: Email to include in the token
        is_superuser: Whether the user is a superuser
        expired: Whether the token should be expired

    Returns:
        JWT token string
    """
    settings = get_settings()

    now = datetime.now(timezone.utc)
    if expired:
        exp = now - timedelta(hours=1)
    else:
        exp = now + timedelta(hours=1)

    payload = {
        "sub": str(user_id),
        "email": email,
        "is_superuser": is_superuser,
        "exp": exp,
        "iat": now,
    }

    return jwt.encode(
        payload,
        settings.JARVIS_AUTH_SECRET_KEY,
        algorithm=settings.JARVIS_AUTH_ALGORITHM,
    )


@pytest.fixture
def superuser_token() -> str:
    """Create a valid superuser JWT token."""
    return create_test_jwt(
        user_id=1,
        email="admin@example.com",
        is_superuser=True,
    )


@pytest.fixture
def regular_user_token() -> str:
    """Create a valid regular user JWT token."""
    return create_test_jwt(
        user_id=2,
        email="user@example.com",
        is_superuser=False,
    )


@pytest.fixture
def expired_superuser_token() -> str:
    """Create an expired superuser JWT token."""
    return create_test_jwt(
        user_id=1,
        email="admin@example.com",
        is_superuser=True,
        expired=True,
    )
