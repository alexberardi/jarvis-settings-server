"""Pydantic models for jarvis-settings-server."""

from typing import Any

from pydantic import BaseModel


# ===========================================================================
# Service Discovery Models
# ===========================================================================


class ServiceInfo(BaseModel):
    """Information about a service from config-service."""

    name: str
    host: str
    port: int
    scheme: str = "http"
    url: str
    health_path: str = "/health"
    description: str | None = None


class ServiceListResponse(BaseModel):
    """Response from config-service /services endpoint."""

    services: list[ServiceInfo]


# ===========================================================================
# Settings Models (mirrored from jarvis-settings-client)
# ===========================================================================


class SettingResponse(BaseModel):
    """Response for a single setting."""

    key: str
    value: Any
    value_type: str
    category: str
    description: str | None
    requires_reload: bool
    is_secret: bool
    env_fallback: str | None = None
    from_db: bool


class SettingsListResponse(BaseModel):
    """Response for listing settings from a single service."""

    settings: list[SettingResponse]
    total: int


class SettingUpdate(BaseModel):
    """Request to update a single setting."""

    value: Any


class UpdateResponse(BaseModel):
    """Response for update operation."""

    success: bool
    key: str
    requires_reload: bool
    message: str | None = None


# ===========================================================================
# Aggregated Settings Models
# ===========================================================================


class ServiceSettingsResult(BaseModel):
    """Settings result from a single service."""

    service_name: str
    success: bool
    settings: list[SettingResponse] = []
    error: str | None = None
    latency_ms: float | None = None


class AggregatedSettingsResponse(BaseModel):
    """Aggregated settings from multiple services."""

    services: list[ServiceSettingsResult]
    total_services: int
    successful_services: int
    failed_services: int


class ServiceSettingsResponse(BaseModel):
    """Settings from a single service."""

    service_name: str
    settings: list[SettingResponse]
    total: int


class ServiceUpdateResponse(BaseModel):
    """Response for updating a setting on a service."""

    service_name: str
    success: bool
    key: str
    requires_reload: bool
    message: str | None = None
    error: str | None = None


