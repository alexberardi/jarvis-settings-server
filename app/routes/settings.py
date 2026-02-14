"""Settings aggregation routes.

Provides endpoints to fetch and update settings across all Jarvis services.
"""

from fastapi import APIRouter, Depends, Header, HTTPException, Query, status
import httpx

from app.auth import require_superuser, SuperuserUser
from app.schemas import (
    AggregatedSettingsResponse,
    ServiceSettingsResponse,
    ServiceSettingsResult,
    ServiceUpdateResponse,
    SettingUpdate,
)
from app.services import (
    get_services,
    get_service_by_name,
    fetch_service_settings,
    fetch_all_services_settings,
    update_service_setting,
)
from app.services.service_discovery import get_settings_url


router = APIRouter(prefix="/v1/settings", tags=["settings"])


def _extract_token(authorization: str) -> str:
    """Extract the token from the Authorization header."""
    if authorization.startswith("Bearer "):
        return authorization[7:]
    return authorization


@router.get("/", response_model=AggregatedSettingsResponse)
async def list_all_settings(
    service: str | None = Query(None, description="Filter by service name"),
    category: str | None = Query(None, description="Filter by category"),
    authorization: str = Header(...),
    _auth: SuperuserUser = Depends(require_superuser),
) -> AggregatedSettingsResponse:
    """Get settings from all services (or a specific service).

    This endpoint aggregates settings from all registered Jarvis services.
    Use the `service` query parameter to filter to a specific service.
    Use the `category` query parameter to filter by settings category.

    Requires superuser JWT authentication.
    """
    token = _extract_token(authorization)

    try:
        services = await get_services(service_filter=service)
    except httpx.HTTPError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Failed to fetch services from config-service: {exc}",
        ) from exc

    if not services:
        if service:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Service '{service}' not found in registry",
            )
        return AggregatedSettingsResponse(
            services=[],
            total_services=0,
            successful_services=0,
            failed_services=0,
        )

    results = await fetch_all_services_settings(services, token, category)

    successful = sum(1 for r in results if r.success)
    failed = len(results) - successful

    return AggregatedSettingsResponse(
        services=results,
        total_services=len(results),
        successful_services=successful,
        failed_services=failed,
    )


@router.get("/{service_name}", response_model=ServiceSettingsResponse)
async def get_service_settings(
    service_name: str,
    category: str | None = Query(None, description="Filter by category"),
    authorization: str = Header(...),
    _auth: SuperuserUser = Depends(require_superuser),
) -> ServiceSettingsResponse:
    """Get settings from a specific service.

    Requires superuser JWT authentication.
    """
    token = _extract_token(authorization)

    try:
        service = await get_service_by_name(service_name)
    except httpx.HTTPError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Failed to fetch service from config-service: {exc}",
        ) from exc

    if not service:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Service '{service_name}' not found in registry",
        )

    result = await fetch_service_settings(service, token, category)

    if not result.success:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Failed to fetch settings from {service_name}: {result.error}",
        )

    return ServiceSettingsResponse(
        service_name=service_name,
        settings=result.settings,
        total=len(result.settings),
    )


@router.put("/{service_name}/{key:path}", response_model=ServiceUpdateResponse)
async def update_setting(
    service_name: str,
    key: str,
    body: SettingUpdate,
    authorization: str = Header(...),
    _auth: SuperuserUser = Depends(require_superuser),
) -> ServiceUpdateResponse:
    """Update a setting on a specific service.

    The key uses dot notation, e.g., `model.main.name`.

    Requires superuser JWT authentication.
    """
    token = _extract_token(authorization)

    try:
        service = await get_service_by_name(service_name)
    except httpx.HTTPError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Failed to fetch service from config-service: {exc}",
        ) from exc

    if not service:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Service '{service_name}' not found in registry",
        )

    try:
        result = await update_service_setting(service, token, key, body.value)
    except httpx.ConnectError:
        return ServiceUpdateResponse(
            service_name=service_name,
            success=False,
            key=key,
            requires_reload=False,
            error="Connection refused",
        )
    except httpx.TimeoutException:
        return ServiceUpdateResponse(
            service_name=service_name,
            success=False,
            key=key,
            requires_reload=False,
            error="Request timeout",
        )
    except httpx.RequestError as exc:
        return ServiceUpdateResponse(
            service_name=service_name,
            success=False,
            key=key,
            requires_reload=False,
            error=f"{type(exc).__name__}: {exc}",
        )

    return ServiceUpdateResponse(
        service_name=service_name,
        success=result.success,
        key=key,
        requires_reload=result.requires_reload,
        message=result.message,
        error=None if result.success else result.message,
    )


@router.get("/{service_name}/url", response_model=dict)
async def get_service_settings_url(
    service_name: str,
    _auth: SuperuserUser = Depends(require_superuser),
) -> dict:
    """Get the settings URL for a specific service.

    This is useful for debugging and understanding the service mapping.

    Requires superuser JWT authentication.
    """
    try:
        service = await get_service_by_name(service_name)
    except httpx.HTTPError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Failed to fetch service from config-service: {exc}",
        ) from exc

    if not service:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Service '{service_name}' not found in registry",
        )

    return {
        "service_name": service_name,
        "base_url": service.url,
        "settings_url": get_settings_url(service),
    }
