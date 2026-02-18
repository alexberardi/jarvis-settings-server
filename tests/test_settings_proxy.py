"""Tests for settings proxy module."""

import pytest
import respx
from httpx import Response

from app.schemas import ServiceInfo
from app.services.settings_proxy import (
    fetch_service_settings,
    fetch_all_services_settings,
    update_service_setting,
)


@pytest.fixture
def sample_service() -> ServiceInfo:
    """Create a sample service for testing."""
    return ServiceInfo(
        name="jarvis-auth",
        host="localhost",
        port=7701,
        scheme="http",
        url="http://localhost:7701",
        health_path="/health",
    )


@pytest.fixture
def sample_token() -> str:
    """Sample JWT token for testing."""
    return "test-token-123"


class TestFetchServiceSettings:
    """Test fetching settings from a single service."""

    @respx.mock
    @pytest.mark.asyncio
    async def test_successful_fetch(self, sample_service, sample_token):
        """Should fetch settings successfully."""
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
                            "description": "Timeout in seconds",
                            "requires_reload": False,
                            "is_secret": False,
                            "from_db": False,
                        }
                    ],
                    "total": 1,
                },
            )
        )

        result = await fetch_service_settings(sample_service, sample_token)

        assert result.success is True
        assert result.service_name == "jarvis-auth"
        assert len(result.settings) == 1
        assert result.settings[0].key == "auth.timeout"
        assert result.latency_ms is not None

    @respx.mock
    @pytest.mark.asyncio
    async def test_with_category_filter(self, sample_service, sample_token):
        """Should pass category filter to service."""
        respx.get("http://localhost:7701/settings", params={"category": "model"}).mock(
            return_value=Response(
                200,
                json={"settings": [], "total": 0},
            )
        )

        result = await fetch_service_settings(sample_service, sample_token, category="model")

        assert result.success is True

    @respx.mock
    @pytest.mark.asyncio
    async def test_handles_http_error(self, sample_service, sample_token):
        """Should handle HTTP errors gracefully."""
        respx.get("http://localhost:7701/settings").mock(
            return_value=Response(500, text="Internal Server Error")
        )

        result = await fetch_service_settings(sample_service, sample_token)

        assert result.success is False
        assert result.error is not None
        assert "500" in result.error

    @respx.mock
    @pytest.mark.asyncio
    async def test_handles_connection_error(self, sample_service, sample_token):
        """Should handle connection errors gracefully."""
        import httpx as httpx_lib

        respx.get("http://localhost:7701/settings").mock(
            side_effect=httpx_lib.ConnectError("Connection refused")
        )

        result = await fetch_service_settings(sample_service, sample_token)

        assert result.success is False
        assert result.error is not None
        assert "Connection refused" in result.error

    @respx.mock
    @pytest.mark.asyncio
    async def test_handles_timeout_error(self, sample_service, sample_token):
        """Should handle timeout errors gracefully."""
        import httpx as httpx_lib

        respx.get("http://localhost:7701/settings").mock(
            side_effect=httpx_lib.ReadTimeout("Read timed out")
        )

        result = await fetch_service_settings(sample_service, sample_token)

        assert result.success is False
        assert result.error is not None
        assert "timeout" in result.error.lower()

    @respx.mock
    @pytest.mark.asyncio
    async def test_handles_generic_request_error(self, sample_service, sample_token):
        """Should handle generic request errors gracefully."""
        import httpx as httpx_lib

        respx.get("http://localhost:7701/settings").mock(
            side_effect=httpx_lib.RequestError("Something broke")
        )

        result = await fetch_service_settings(sample_service, sample_token)

        assert result.success is False
        assert result.error is not None


class TestFetchAllServicesSettings:
    """Test fetching settings from multiple services."""

    @respx.mock
    @pytest.mark.asyncio
    async def test_fetches_from_multiple_services(self, sample_token):
        """Should fetch from all services concurrently."""
        services = [
            ServiceInfo(
                name="jarvis-auth",
                host="localhost",
                port=7701,
                scheme="http",
                url="http://localhost:7701",
            ),
            ServiceInfo(
                name="jarvis-logs",
                host="localhost",
                port=7702,
                scheme="http",
                url="http://localhost:7702",
            ),
        ]

        respx.get("http://localhost:7701/settings").mock(
            return_value=Response(200, json={"settings": [], "total": 0})
        )
        respx.get("http://localhost:7702/settings").mock(
            return_value=Response(200, json={"settings": [], "total": 0})
        )

        results = await fetch_all_services_settings(services, sample_token)

        assert len(results) == 2
        assert all(r.success for r in results)

    @respx.mock
    @pytest.mark.asyncio
    async def test_handles_partial_failures(self, sample_token):
        """Should handle some services failing."""
        services = [
            ServiceInfo(
                name="jarvis-auth",
                host="localhost",
                port=7701,
                scheme="http",
                url="http://localhost:7701",
            ),
            ServiceInfo(
                name="jarvis-broken",
                host="localhost",
                port=9999,
                scheme="http",
                url="http://localhost:9999",
            ),
        ]

        respx.get("http://localhost:7701/settings").mock(
            return_value=Response(200, json={"settings": [], "total": 0})
        )
        respx.get("http://localhost:9999/settings").mock(
            return_value=Response(500, text="Error")
        )

        results = await fetch_all_services_settings(services, sample_token)

        assert len(results) == 2
        assert results[0].success is True
        assert results[1].success is False


class TestUpdateServiceSetting:
    """Test updating a setting on a service."""

    @respx.mock
    @pytest.mark.asyncio
    async def test_successful_update(self, sample_service, sample_token):
        """Should update setting successfully."""
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

        result = await update_service_setting(
            sample_service, sample_token, "auth.timeout", 60
        )

        assert result.success is True
        assert result.key == "auth.timeout"

    @respx.mock
    @pytest.mark.asyncio
    async def test_setting_not_found(self, sample_service, sample_token):
        """Should handle setting not found."""
        respx.put("http://localhost:7701/settings/unknown.key").mock(
            return_value=Response(404, text="Not found")
        )

        result = await update_service_setting(
            sample_service, sample_token, "unknown.key", "value"
        )

        assert result.success is False
        assert "not found" in result.message.lower()

    @respx.mock
    @pytest.mark.asyncio
    async def test_requires_reload_flag(self, sample_service, sample_token):
        """Should pass through requires_reload flag."""
        respx.put("http://localhost:7701/settings/auth.secret").mock(
            return_value=Response(
                200,
                json={
                    "success": True,
                    "key": "auth.secret",
                    "requires_reload": True,
                    "message": "Service restart required",
                },
            )
        )

        result = await update_service_setting(
            sample_service, sample_token, "auth.secret", "new-secret"
        )

        assert result.success is True
        assert result.requires_reload is True

    @respx.mock
    @pytest.mark.asyncio
    async def test_handles_server_error(self, sample_service, sample_token):
        """Should handle non-200/404 responses."""
        respx.put("http://localhost:7701/settings/auth.timeout").mock(
            return_value=Response(500, text="Internal Server Error")
        )

        result = await update_service_setting(
            sample_service, sample_token, "auth.timeout", 60
        )

        assert result.success is False
        assert "500" in result.message
