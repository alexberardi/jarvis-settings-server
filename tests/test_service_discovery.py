"""Tests for service discovery module."""

import pytest
import respx
from httpx import Response

from app.services.service_discovery import (
    EXCLUDED_SERVICES,
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
        """Command center uses /settings."""
        assert get_settings_path("jarvis-command-center") == "/settings"

    def test_auth_path(self):
        """Auth uses /settings."""
        assert get_settings_path("jarvis-auth") == "/settings"

    def test_default_path(self):
        """Unknown services use /settings (jarvis-settings-client convention)."""
        assert get_settings_path("some-unknown-service") == "/settings"
        assert get_settings_path("jarvis-logs") == "/settings"


class TestGetSettingsUrl:
    """Test full settings URL construction."""

    def test_builds_full_url(self):
        """Should build full URL from service info."""
        service = ServiceInfo(
            name="jarvis-auth",
            host="localhost",
            port=7701,
            scheme="http",
            url="http://localhost:7701",
        )

        url = get_settings_url(service)
        assert url == "http://localhost:7701/settings"

    def test_builds_url_with_default_path(self):
        """Should use default path for unknown services."""
        service = ServiceInfo(
            name="jarvis-logs",
            host="localhost",
            port=7702,
            scheme="http",
            url="http://localhost:7702",
        )

        url = get_settings_url(service)
        assert url == "http://localhost:7702/settings"


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

        services = await get_services(service_filter="jarvis-auth")

        assert len(services) == 1
        assert services[0].name == "jarvis-auth"

    @respx.mock
    @pytest.mark.asyncio
    async def test_excludes_non_settings_services(self, settings):
        """Should exclude self, mcp, and config-service from results."""
        all_services = [
            {
                "name": "jarvis-auth",
                "host": "localhost",
                "port": 7701,
                "scheme": "http",
                "url": "http://localhost:7701",
                "health_path": "/health",
            },
        ]
        # Add all excluded services to the response
        for name in EXCLUDED_SERVICES:
            all_services.append({
                "name": name,
                "host": "localhost",
                "port": 9999,
                "scheme": "http",
                "url": "http://localhost:9999",
                "health_path": "/health",
            })

        respx.get(f"{settings.JARVIS_CONFIG_URL}/services").mock(
            return_value=Response(200, json={"services": all_services})
        )

        services = await get_services()

        assert len(services) == 1
        assert services[0].name == "jarvis-auth"
        returned_names = {s.name for s in services}
        assert returned_names.isdisjoint(EXCLUDED_SERVICES)


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
                            "port": 7701,
                            "scheme": "http",
                            "url": "http://localhost:7701",
                            "health_path": "/health",
                        },
                    ]
                },
            )
        )

        service = await get_service_by_name("jarvis-auth")

        assert service is not None
        assert service.name == "jarvis-auth"
        assert service.port == 7701

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
