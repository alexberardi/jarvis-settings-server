"""Tests for service discovery module."""

import pytest
import respx
from httpx import Response

from app.services.service_discovery import (
    get_settings_path,
    get_settings_url,
    get_services,
    get_service_by_name,
)
from app.schemas import ServiceInfo


class TestGetSettingsPath:
    """Test settings path mapping."""

    def test_llm_proxy_path(self):
        """LLM proxy uses /settings."""
        assert get_settings_path("jarvis-llm-proxy-api") == "/settings"

    def test_command_center_path(self):
        """Command center uses /api/v0/settings."""
        assert get_settings_path("jarvis-command-center") == "/api/v0/settings"

    def test_auth_path(self):
        """Auth uses /settings."""
        assert get_settings_path("jarvis-auth") == "/settings"

    def test_default_path(self):
        """Unknown services use /v1/settings."""
        assert get_settings_path("some-unknown-service") == "/v1/settings"
        assert get_settings_path("jarvis-logs") == "/v1/settings"


class TestGetSettingsUrl:
    """Test full settings URL construction."""

    def test_builds_full_url(self):
        """Should build full URL from service info."""
        service = ServiceInfo(
            name="jarvis-auth",
            host="localhost",
            port=8007,
            scheme="http",
            url="http://localhost:8007",
        )

        url = get_settings_url(service)
        assert url == "http://localhost:8007/settings"

    def test_builds_url_with_default_path(self):
        """Should use default path for unknown services."""
        service = ServiceInfo(
            name="jarvis-logs",
            host="localhost",
            port=8006,
            scheme="http",
            url="http://localhost:8006",
        )

        url = get_settings_url(service)
        assert url == "http://localhost:8006/v1/settings"


class TestGetServices:
    """Test service discovery from config service."""

    @respx.mock
    @pytest.mark.asyncio
    async def test_fetches_all_services(self, settings):
        """Should fetch all services from config service."""
        respx.get(f"{settings.JARVIS_CONFIG_URL}/services").mock(
            return_value=Response(
                200,
                json={
                    "services": [
                        {
                            "name": "jarvis-auth",
                            "host": "localhost",
                            "port": 8007,
                            "scheme": "http",
                            "url": "http://localhost:8007",
                            "health_path": "/health",
                        },
                        {
                            "name": "jarvis-logs",
                            "host": "localhost",
                            "port": 8006,
                            "scheme": "http",
                            "url": "http://localhost:8006",
                            "health_path": "/health",
                        },
                    ]
                },
            )
        )

        services = await get_services()

        assert len(services) == 2
        assert services[0].name == "jarvis-auth"
        assert services[1].name == "jarvis-logs"

    @respx.mock
    @pytest.mark.asyncio
    async def test_filters_by_name(self, settings):
        """Should filter services by name."""
        respx.get(f"{settings.JARVIS_CONFIG_URL}/services").mock(
            return_value=Response(
                200,
                json={
                    "services": [
                        {
                            "name": "jarvis-auth",
                            "host": "localhost",
                            "port": 8007,
                            "scheme": "http",
                            "url": "http://localhost:8007",
                            "health_path": "/health",
                        },
                        {
                            "name": "jarvis-logs",
                            "host": "localhost",
                            "port": 8006,
                            "scheme": "http",
                            "url": "http://localhost:8006",
                            "health_path": "/health",
                        },
                    ]
                },
            )
        )

        services = await get_services(service_filter="jarvis-auth")

        assert len(services) == 1
        assert services[0].name == "jarvis-auth"


class TestGetServiceByName:
    """Test getting a single service by name."""

    @respx.mock
    @pytest.mark.asyncio
    async def test_finds_service(self, settings):
        """Should find service by name."""
        respx.get(f"{settings.JARVIS_CONFIG_URL}/services").mock(
            return_value=Response(
                200,
                json={
                    "services": [
                        {
                            "name": "jarvis-auth",
                            "host": "localhost",
                            "port": 8007,
                            "scheme": "http",
                            "url": "http://localhost:8007",
                            "health_path": "/health",
                        },
                    ]
                },
            )
        )

        service = await get_service_by_name("jarvis-auth")

        assert service is not None
        assert service.name == "jarvis-auth"
        assert service.port == 8007

    @respx.mock
    @pytest.mark.asyncio
    async def test_returns_none_for_unknown(self, settings):
        """Should return None for unknown service."""
        respx.get(f"{settings.JARVIS_CONFIG_URL}/services").mock(
            return_value=Response(
                200,
                json={"services": []},
            )
        )

        service = await get_service_by_name("unknown-service")

        assert service is None
