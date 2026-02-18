"""Service discovery via jarvis-config-service.

Fetches the list of registered services and maps them to their settings endpoints.
"""

import httpx

from app.config import get_settings
from app.schemas import ServiceInfo, ServiceListResponse


# Services to exclude from settings aggregation
EXCLUDED_SERVICES: set[str] = {
    "jarvis-settings-server",  # Self — would create circular request
    "jarvis-mcp",              # No settings endpoint
    "jarvis-config-service",   # No settings endpoint
}

# Map service names to their settings path
# All services use /settings by default (jarvis-settings-client convention)
# Add overrides here only if a service uses a non-standard path
SETTINGS_PATHS: dict[str, str] = {}


def get_settings_path(service_name: str) -> str:
    """Get the settings endpoint path for a service.

    Args:
        service_name: Name of the service

    Returns:
        The path to the settings endpoint (e.g., "/settings")
    """
    return SETTINGS_PATHS.get(service_name, "/settings")


def get_settings_url(service: ServiceInfo) -> str:
    """Get the full settings URL for a service.

    Args:
        service: ServiceInfo object

    Returns:
        Full URL to the settings endpoint
    """
    path = get_settings_path(service.name)
    return f"{service.url}{path}"


async def get_services(
    service_filter: str | None = None,
) -> list[ServiceInfo]:
    """Get list of services from jarvis-config-service.

    Args:
        service_filter: Optional service name to filter by

    Returns:
        List of ServiceInfo objects

    Raises:
        httpx.HTTPError: If the request fails
    """
    settings = get_settings()

    async with httpx.AsyncClient(timeout=settings.SERVICE_TIMEOUT) as client:
        response = await client.get(f"{settings.JARVIS_CONFIG_URL}/services")
        response.raise_for_status()

        data = response.json()
        service_list = ServiceListResponse(**data)

        services = [
            s for s in service_list.services
            if s.name not in EXCLUDED_SERVICES
        ]

        if service_filter:
            return [s for s in services if s.name == service_filter]

        return services


async def get_service_by_name(service_name: str) -> ServiceInfo | None:
    """Get a specific service by name.

    Args:
        service_name: Name of the service to find

    Returns:
        ServiceInfo if found, None otherwise
    """
    services = await get_services(service_filter=service_name)
    return services[0] if services else None
