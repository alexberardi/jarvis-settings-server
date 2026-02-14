"""Tests for authentication module.

Now uses jarvis-auth-client under the hood. These tests verify
that the integration works correctly via app.auth.
"""

import pytest
from fastapi import HTTPException

from app.auth import require_superuser
from jarvis_auth_client import SuperuserUser
from jarvis_auth_client.client import _decode_jwt
from tests.conftest import create_test_jwt


class TestDecodeJWT:
    """Test JWT decoding."""

    def test_decode_valid_token(self, settings):
        """Should decode a valid token."""
        token = create_test_jwt(user_id=1, email="test@example.com", is_superuser=True)
        payload = _decode_jwt(token)

        assert payload["sub"] == "1"
        assert payload["email"] == "test@example.com"
        assert payload["is_superuser"] is True

    def test_decode_expired_token_raises(self, settings):
        """Should raise HTTPException for expired token."""
        token = create_test_jwt(is_superuser=True, expired=True)

        with pytest.raises(HTTPException) as exc:
            _decode_jwt(token)

        assert exc.value.status_code == 401
        assert "expired" in exc.value.detail.lower()

    def test_decode_invalid_token_raises(self, settings):
        """Should raise HTTPException for invalid token."""
        with pytest.raises(HTTPException) as exc:
            _decode_jwt("invalid-token")

        assert exc.value.status_code == 401


class TestRequireSuperuser:
    """Test require_superuser dependency."""

    def test_missing_authorization_header(self):
        """Should raise 401 when Authorization header is missing."""
        with pytest.raises(HTTPException) as exc:
            require_superuser(authorization=None)

        assert exc.value.status_code == 401
        assert "Missing" in exc.value.detail

    def test_invalid_authorization_format(self):
        """Should raise 401 when Authorization format is wrong."""
        with pytest.raises(HTTPException) as exc:
            require_superuser(authorization="Basic abc123")

        assert exc.value.status_code == 401
        assert "format" in exc.value.detail.lower()

    def test_regular_user_forbidden(self, regular_user_token):
        """Should raise 403 when user is not a superuser."""
        with pytest.raises(HTTPException) as exc:
            require_superuser(authorization=f"Bearer {regular_user_token}")

        assert exc.value.status_code == 403
        assert "superuser" in exc.value.detail.lower()

    def test_superuser_allowed(self, superuser_token):
        """Should return SuperuserUser for superuser."""
        user = require_superuser(authorization=f"Bearer {superuser_token}")

        assert isinstance(user, SuperuserUser)
        assert user.auth_type == "superuser_jwt"
        assert user.user_id == 1
        assert user.email == "admin@example.com"

    def test_expired_token_rejected(self, expired_superuser_token):
        """Should reject expired tokens."""
        with pytest.raises(HTTPException) as exc:
            require_superuser(authorization=f"Bearer {expired_superuser_token}")

        assert exc.value.status_code == 401
