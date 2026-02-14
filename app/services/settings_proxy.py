"""Settings proxy service.

Fetches settings from individual services and aggregates them.
"""

import asyncio
import time
from typing import Any

import httpx

from app.config import get_settings
from app.schemas import (
    ServiceInfo,
    ServiceSettingsResult,
    SettingResponse,
    SettingsListResponse,
    UpdateResponse,
)
from app.services.service_discovery import get_settings_url


async def fetch_service_settings(
    service: ServiceInfo,
    token: str,
    category: str | None = None,
) -> ServiceSettingsResult:
    """Fetch settings from a single service.

    Args:
        service: ServiceInfo object for the target service
        token: Superuser JWT token for authentication
        category: Optional category filter

    Returns:
        ServiceSettingsResult with settings or error
    """
    settings = get_settings()
    settings_url = get_settings_url(service)

    params: dict[str, str] = {}
    if category:
        params["category"] = category

    start_time = time.time()

    try:
        async with httpx.AsyncClient(timeout=settings.SERVICE_TIMEOUT) as client:
            response = await client.get(
                settings_url,
                params=params if params else None,
                headers={"Authorization": f"Bearer {token}"},
            )

            latency_ms = (time.time() - start_time) * 1000

            if response.status_code == 200:
                data = response.json()
                settings_list = SettingsListResponse(**data)
                return ServiceSettingsResult(
                    service_name=service.name,
                    success=True,
                    settings=settings_list.settings,
                    latency_ms=round(latency_ms, 2),
                )
            else:
                return ServiceSettingsResult(
                    service_name=service.name,
                    success=False,
                    error=f"HTTP {response.status_code}: {response.text[:200]}",
                    latency_ms=round(latency_ms, 2),
                )

    except httpx.ConnectError:
        return ServiceSettingsResult(
            service_name=service.name,
            success=False,
            error="Connection refused",
        )
    except httpx.TimeoutException:
        return ServiceSettingsResult(
            service_name=service.name,
            success=False,
            error="Request timeout",
        )
    except httpx.RequestError as exc:
        return ServiceSettingsResult(
            service_name=service.name,
            success=False,
            error=f"{type(exc).__name__}: {exc}",
        )


async def fetch_all_services_settings(
    services: list[ServiceInfo],
    token: str,
    category: str | None = None,
) -> list[ServiceSettingsResult]:
    """Fetch settings from multiple services concurrently.

    Args:
        services: List of services to fetch settings from
        token: Superuser JWT token for authentication
        category: Optional category filter

    Returns:
        List of ServiceSettingsResult for each service
    """
    tasks = [
        fetch_service_settings(service, token, category)
        for service in services
    ]

    results = await asyncio.gather(*tasks, return_exceptions=True)

    # Convert any exceptions to error results
    final_results: list[ServiceSettingsResult] = []
    for i, result in enumerate(results):
        if isinstance(result, Exception):
            final_results.append(
                ServiceSettingsResult(
                    service_name=services[i].name,
                    success=False,
                    error=f"{type(result).__name__}: {result}",
                )
            )
        else:
            final_results.append(result)

    return final_results


async def update_service_setting(
    service: ServiceInfo,
    token: str,
    key: str,
    value: Any,
) -> UpdateResponse:
    """Update a setting on a specific service.

    Args:
        service: ServiceInfo object for the target service
        token: Superuser JWT token for authentication
        key: Setting key to update
        value: New value for the setting

    Returns:
        UpdateResponse with result

    Raises:
        httpx.HTTPError: If the request fails
    """
    settings = get_settings()
    settings_url = get_settings_url(service)
    update_url = f"{settings_url}/{key}"

    async with httpx.AsyncClient(timeout=settings.SERVICE_TIMEOUT) as client:
        response = await client.put(
            update_url,
            json={"value": value},
            headers={"Authorization": f"Bearer {token}"},
        )

        if response.status_code == 200:
            data = response.json()
            return UpdateResponse(**data)
        elif response.status_code == 404:
            return UpdateResponse(
                success=False,
                key=key,
                requires_reload=False,
                message=f"Setting not found: {key}",
            )
        else:
            return UpdateResponse(
                success=False,
                key=key,
                requires_reload=False,
                message=f"HTTP {response.status_code}: {response.text[:200]}",
            )
