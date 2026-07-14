"""Tests for settings routes."""

import pytest
import respx
from httpx import Response

from app.routes.settings import _extract_token


class TestExtractToken:
    """Test token extraction from Authorization header."""

    def test_extracts_bearer_token(self):
        """Should strip 'Bearer ' prefix."""
        assert _extract_token("Bearer abc123") == "abc123"

    def test_returns_raw_when_no_bearer(self):
        """Should return raw value when not Bearer format."""
        assert _extract_token("abc123") == "abc123"


class TestHealthEndpoint:
    """Test health check endpoint."""

    def test_health_returns_ok(self, client):
        """Health endpoint should return ok."""
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert data["service"] == "jarvis-settings-server"


class TestListAllSettings:
    """Test GET /v1/settings/ endpoint."""

    def test_requires_auth(self, client):
        """Should require authentication."""
        response = client.get("/v1/settings/")
        assert response.status_code == 401

    def test_rejects_regular_user(self, client, regular_user_token):
        """Should reject non-superuser."""
        response = client.get(
            "/v1/settings/",
            headers={"Authorization": f"Bearer {regular_user_token}"},
        )
        assert response.status_code == 403

    @respx.mock
    def test_fetches_services_from_config(self, client, superuser_token, settings):
        """Should fetch services from config service."""
        # Mock config service response
        respx.get(f"{settings.JARVIS_CONFIG_URL}/services").mock(
            return_value=Response(
                200,
                json={
                    "services": [
                        {
                            "name": "jarvis-auth",
                            "host": "localhost",
                            "port": 7701,
                            "scheme": "http",
                            "url": "http://localhost:7701",
                            "health_path": "/health",
                        }
                    ]
                },
            )
        )

        # Mock settings endpoint on jarvis-auth
        respx.get("http://localhost:7701/settings").mock(
            return_value=Response(
                200,
                json={
                    "settings": [
                        {
                            "key": "test.setting",
                            "value": "test-value",
                            "value_type": "string",
                            "category": "test",
                            "description": "A test setting",
                            "requires_reload": False,
                            "is_secret": False,
                            "from_db": False,
                        }
                    ],
                    "total": 1,
                },
            )
        )

        response = client.get(
            "/v1/settings/",
            headers={"Authorization": f"Bearer {superuser_token}"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["total_services"] == 1
        assert data["successful_services"] == 1
        assert len(data["services"]) == 1
        assert data["services"][0]["service_name"] == "jarvis-auth"

    @respx.mock
    def test_service_filter(self, client, superuser_token, settings):
        """Should filter by service name."""
        # Mock config service response with multiple services
        respx.get(f"{settings.JARVIS_CONFIG_URL}/services").mock(
            return_value=Response(
                200,
                json={
                    "services": [
                        {
                            "name": "jarvis-auth",
                            "host": "localhost",
                            "port": 7701,
                            "scheme": "http",
                            "url": "http://localhost:7701",
                            "health_path": "/health",
                        },
                        {
                            "name": "jarvis-logs",
                            "host": "localhost",
                            "port": 7702,
                            "scheme": "http",
                            "url": "http://localhost:7702",
                            "health_path": "/health",
                        },
                    ]
                },
            )
        )

        # Mock settings endpoint for jarvis-auth only
        respx.get("http://localhost:7701/settings").mock(
            return_value=Response(
                200,
                json={"settings": [], "total": 0},
            )
        )

        response = client.get(
            "/v1/settings/?service=jarvis-auth",
            headers={"Authorization": f"Bearer {superuser_token}"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["total_services"] == 1
        assert data["services"][0]["service_name"] == "jarvis-auth"

    @respx.mock
    def test_handles_config_service_error(self, client, superuser_token, settings):
        """Should return 503 when config service is unavailable."""
        respx.get(f"{settings.JARVIS_CONFIG_URL}/services").mock(
            return_value=Response(500)
        )

        response = client.get(
            "/v1/settings/",
            headers={"Authorization": f"Bearer {superuser_token}"},
        )

        assert response.status_code == 503


class TestGetServiceSettingsFilters:
    """GET /v1/settings/{service} — service and category filtering.

    Renamed 2026-07-14. This class was named TestGetServiceSettings — identical to
    the class below it. Python overwrites the first definition, so pytest never saw
    these tests: they did not fail, they simply never ran. Two of them
    (empty_services_no_filter, service_filter_not_found) exist nowhere else, so that
    coverage was silently absent while the suite reported green. Found by ruff F811.
    """

    @respx.mock
    def test_get_single_service_settings(self, client, superuser_token, settings):
        """Should get settings from a single service."""
        respx.get(f"{settings.JARVIS_CONFIG_URL}/services").mock(
            return_value=Response(
                200,
                json={
                    "services": [
                        {
                            "name": "jarvis-auth",
                            "host": "localhost",
                            "port": 7701,
                            "scheme": "http",
                            "url": "http://localhost:7701",
                            "health_path": "/health",
                        }
                    ]
                },
            )
        )

        respx.get("http://localhost:7701/settings").mock(
            return_value=Response(
                200,
                json={
                    "settings": [
                        {
                            "key": "auth.timeout",
                            "value": 30,
                            "value_type": "int",
                            "category": "auth",
                            "description": "Auth timeout",
                            "requires_reload": False,
                            "is_secret": False,
                            "from_db": False,
                        }
                    ],
                    "total": 1,
                },
            )
        )

        response = client.get(
            "/v1/settings/jarvis-auth",
            headers={"Authorization": f"Bearer {superuser_token}"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["service_name"] == "jarvis-auth"
        assert data["total"] == 1
        assert data["settings"][0]["key"] == "auth.timeout"

    @respx.mock
    def test_service_not_found(self, client, superuser_token, settings):
        """Should return 404 for unknown service."""
        respx.get(f"{settings.JARVIS_CONFIG_URL}/services").mock(
            return_value=Response(
                200,
                json={"services": []},
            )
        )

        response = client.get(
            "/v1/settings/unknown-service",
            headers={"Authorization": f"Bearer {superuser_token}"},
        )

        assert response.status_code == 404


    @respx.mock
    def test_empty_services_no_filter(self, client, superuser_token, settings):
        """Should return empty aggregation when no services registered."""
        respx.get(f"{settings.JARVIS_CONFIG_URL}/services").mock(
            return_value=Response(200, json={"services": []})
        )

        response = client.get(
            "/v1/settings/",
            headers={"Authorization": f"Bearer {superuser_token}"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["total_services"] == 0
        assert data["successful_services"] == 0
        assert data["failed_services"] == 0
        assert data["services"] == []

    @respx.mock
    def test_service_filter_not_found(self, client, superuser_token, settings):
        """Should return 404 when service filter matches nothing."""
        respx.get(f"{settings.JARVIS_CONFIG_URL}/services").mock(
            return_value=Response(200, json={"services": []})
        )

        response = client.get(
            "/v1/settings/?service=nonexistent",
            headers={"Authorization": f"Bearer {superuser_token}"},
        )

        assert response.status_code == 404

    @respx.mock
    def test_category_filter(self, client, superuser_token, settings):
        """Should pass category filter through to services."""
        respx.get(f"{settings.JARVIS_CONFIG_URL}/services").mock(
            return_value=Response(
                200,
                json={
                    "services": [
                        {
                            "name": "jarvis-auth",
                            "host": "localhost",
                            "port": 7701,
                            "scheme": "http",
                            "url": "http://localhost:7701",
                            "health_path": "/health",
                        }
                    ]
                },
            )
        )

        respx.get("http://localhost:7701/settings").mock(
            return_value=Response(200, json={"settings": [], "total": 0})
        )

        response = client.get(
            "/v1/settings/?category=model",
            headers={"Authorization": f"Bearer {superuser_token}"},
        )

        assert response.status_code == 200


class TestGetServiceSettings:
    """Test GET /v1/settings/{service} endpoint."""

    @respx.mock
    def test_get_single_service_settings(self, client, superuser_token, settings):
        """Should get settings from a single service."""
        respx.get(f"{settings.JARVIS_CONFIG_URL}/services").mock(
            return_value=Response(
                200,
                json={
                    "services": [
                        {
                            "name": "jarvis-auth",
                            "host": "localhost",
                            "port": 7701,
                            "scheme": "http",
                            "url": "http://localhost:7701",
                            "health_path": "/health",
                        }
                    ]
                },
            )
        )

        respx.get("http://localhost:7701/settings").mock(
            return_value=Response(
                200,
                json={
                    "settings": [
                        {
                            "key": "auth.timeout",
                            "value": 30,
                            "value_type": "int",
                            "category": "auth",
                            "description": "Auth timeout",
                            "requires_reload": False,
                            "is_secret": False,
                            "from_db": False,
                        }
                    ],
                    "total": 1,
                },
            )
        )

        response = client.get(
            "/v1/settings/jarvis-auth",
            headers={"Authorization": f"Bearer {superuser_token}"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["service_name"] == "jarvis-auth"
        assert data["total"] == 1
        assert data["settings"][0]["key"] == "auth.timeout"

    @respx.mock
    def test_service_not_found(self, client, superuser_token, settings):
        """Should return 404 for unknown service."""
        respx.get(f"{settings.JARVIS_CONFIG_URL}/services").mock(
            return_value=Response(
                200,
                json={"services": []},
            )
        )

        response = client.get(
            "/v1/settings/unknown-service",
            headers={"Authorization": f"Bearer {superuser_token}"},
        )

        assert response.status_code == 404

    @respx.mock
    def test_config_service_error(self, client, superuser_token, settings):
        """Should return 503 when config service fails."""
        respx.get(f"{settings.JARVIS_CONFIG_URL}/services").mock(
            return_value=Response(500)
        )

        response = client.get(
            "/v1/settings/jarvis-auth",
            headers={"Authorization": f"Bearer {superuser_token}"},
        )

        assert response.status_code == 503

    @respx.mock
    def test_service_fetch_fails_returns_502(self, client, superuser_token, settings):
        """Should return 502 when service settings fetch fails."""
        respx.get(f"{settings.JARVIS_CONFIG_URL}/services").mock(
            return_value=Response(
                200,
                json={
                    "services": [
                        {
                            "name": "jarvis-auth",
                            "host": "localhost",
                            "port": 7701,
                            "scheme": "http",
                            "url": "http://localhost:7701",
                            "health_path": "/health",
                        }
                    ]
                },
            )
        )

        respx.get("http://localhost:7701/settings").mock(
            return_value=Response(500, text="Internal Server Error")
        )

        response = client.get(
            "/v1/settings/jarvis-auth",
            headers={"Authorization": f"Bearer {superuser_token}"},
        )

        assert response.status_code == 502

    @respx.mock
    def test_with_category_filter(self, client, superuser_token, settings):
        """Should pass category filter to service."""
        respx.get(f"{settings.JARVIS_CONFIG_URL}/services").mock(
            return_value=Response(
                200,
                json={
                    "services": [
                        {
                            "name": "jarvis-auth",
                            "host": "localhost",
                            "port": 7701,
                            "scheme": "http",
                            "url": "http://localhost:7701",
                            "health_path": "/health",
                        }
                    ]
                },
            )
        )

        respx.get("http://localhost:7701/settings").mock(
            return_value=Response(200, json={"settings": [], "total": 0})
        )

        response = client.get(
            "/v1/settings/jarvis-auth?category=auth",
            headers={"Authorization": f"Bearer {superuser_token}"},
        )

        assert response.status_code == 200


class TestUpdateSetting:
    """Test PUT /v1/settings/{service}/{key} endpoint."""

    @respx.mock
    def test_update_setting_success(self, client, superuser_token, settings):
        """Should update a setting on a service."""
        respx.get(f"{settings.JARVIS_CONFIG_URL}/services").mock(
            return_value=Response(
                200,
                json={
                    "services": [
                        {
                            "name": "jarvis-auth",
                            "host": "localhost",
                            "port": 7701,
                            "scheme": "http",
                            "url": "http://localhost:7701",
                            "health_path": "/health",
                        }
                    ]
                },
            )
        )

        respx.put("http://localhost:7701/settings/auth.timeout").mock(
            return_value=Response(
                200,
                json={
                    "success": True,
                    "key": "auth.timeout",
                    "requires_reload": False,
                    "message": None,
                },
            )
        )

        response = client.put(
            "/v1/settings/jarvis-auth/auth.timeout",
            json={"value": 60},
            headers={"Authorization": f"Bearer {superuser_token}"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["service_name"] == "jarvis-auth"
        assert data["key"] == "auth.timeout"

    @respx.mock
    def test_update_setting_service_not_found(self, client, superuser_token, settings):
        """Should return 404 for unknown service."""
        respx.get(f"{settings.JARVIS_CONFIG_URL}/services").mock(
            return_value=Response(
                200,
                json={"services": []},
            )
        )

        response = client.put(
            "/v1/settings/unknown-service/some.key",
            json={"value": "new-value"},
            headers={"Authorization": f"Bearer {superuser_token}"},
        )

        assert response.status_code == 404

    @respx.mock
    def test_update_config_service_error(self, client, superuser_token, settings):
        """Should return 503 when config service fails during update."""
        respx.get(f"{settings.JARVIS_CONFIG_URL}/services").mock(
            return_value=Response(500)
        )

        response = client.put(
            "/v1/settings/jarvis-auth/some.key",
            json={"value": "new"},
            headers={"Authorization": f"Bearer {superuser_token}"},
        )

        assert response.status_code == 503

    @respx.mock
    def test_update_connection_error(self, client, superuser_token, settings):
        """Should return error response when service connection refused."""
        import httpx as httpx_lib

        respx.get(f"{settings.JARVIS_CONFIG_URL}/services").mock(
            return_value=Response(
                200,
                json={
                    "services": [
                        {
                            "name": "jarvis-auth",
                            "host": "localhost",
                            "port": 7701,
                            "scheme": "http",
                            "url": "http://localhost:7701",
                            "health_path": "/health",
                        }
                    ]
                },
            )
        )

        respx.put("http://localhost:7701/settings/auth.timeout").mock(
            side_effect=httpx_lib.ConnectError("Connection refused")
        )

        response = client.put(
            "/v1/settings/jarvis-auth/auth.timeout",
            json={"value": 60},
            headers={"Authorization": f"Bearer {superuser_token}"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is False
        assert data["error"] == "Connection refused"

    @respx.mock
    def test_update_timeout_error(self, client, superuser_token, settings):
        """Should return error response on timeout."""
        import httpx as httpx_lib

        respx.get(f"{settings.JARVIS_CONFIG_URL}/services").mock(
            return_value=Response(
                200,
                json={
                    "services": [
                        {
                            "name": "jarvis-auth",
                            "host": "localhost",
                            "port": 7701,
                            "scheme": "http",
                            "url": "http://localhost:7701",
                            "health_path": "/health",
                        }
                    ]
                },
            )
        )

        respx.put("http://localhost:7701/settings/auth.timeout").mock(
            side_effect=httpx_lib.ReadTimeout("Read timed out")
        )

        response = client.put(
            "/v1/settings/jarvis-auth/auth.timeout",
            json={"value": 60},
            headers={"Authorization": f"Bearer {superuser_token}"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is False
        assert data["error"] == "Request timeout"


class TestGetServiceSettingsUrl:
    """Test GET /v1/settings/{service}/url endpoint."""

    @respx.mock
    def test_returns_url(self, client, superuser_token, settings):
        """Should return the settings URL for a service."""
        respx.get(f"{settings.JARVIS_CONFIG_URL}/services").mock(
            return_value=Response(
                200,
                json={
                    "services": [
                        {
                            "name": "jarvis-auth",
                            "host": "localhost",
                            "port": 7701,
                            "scheme": "http",
                            "url": "http://localhost:7701",
                            "health_path": "/health",
                        }
                    ]
                },
            )
        )

        response = client.get(
            "/v1/settings/jarvis-auth/url",
            headers={"Authorization": f"Bearer {superuser_token}"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["service_name"] == "jarvis-auth"
        assert data["base_url"] == "http://localhost:7701"
        assert data["settings_url"] == "http://localhost:7701/settings"

    @respx.mock
    def test_service_not_found(self, client, superuser_token, settings):
        """Should return 404 for unknown service."""
        respx.get(f"{settings.JARVIS_CONFIG_URL}/services").mock(
            return_value=Response(200, json={"services": []})
        )

        response = client.get(
            "/v1/settings/unknown-service/url",
            headers={"Authorization": f"Bearer {superuser_token}"},
        )

        assert response.status_code == 404

    @respx.mock
    def test_config_service_error(self, client, superuser_token, settings):
        """Should return 503 when config service fails."""
        respx.get(f"{settings.JARVIS_CONFIG_URL}/services").mock(
            return_value=Response(500)
        )

        response = client.get(
            "/v1/settings/jarvis-auth/url",
            headers={"Authorization": f"Bearer {superuser_token}"},
        )

        assert response.status_code == 503
