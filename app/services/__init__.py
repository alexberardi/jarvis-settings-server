"""Services for jarvis-settings-server."""

from app.services.service_discovery import get_services, get_service_by_name
from app.services.settings_proxy import (
    fetch_service_settings,
    fetch_all_services_settings,
    update_service_setting,
)

__all__ = [
    "get_services",
    "get_service_by_name",
    "fetch_service_settings",
    "fetch_all_services_settings",
    "update_service_setting",
]
