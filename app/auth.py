"""Authentication for jarvis-settings-server.

Only accepts superuser JWT tokens for authentication.
This service is for administrative access to all service settings.
"""

import logging
import os

from jarvis_auth_client import init, require_superuser, SuperuserUser

logger = logging.getLogger("jarvis-settings-server")

# Initialize on import — secret_key must be set via environment
_secret_key = os.getenv("JARVIS_AUTH_SECRET_KEY", "")
_algorithm = os.getenv("JARVIS_AUTH_ALGORITHM", "HS256")

if not _secret_key:
    logger.warning(
        "JARVIS_AUTH_SECRET_KEY not configured — JWT validation will fail! "
        "Set this to match jarvis-auth's SECRET_KEY."
    )
else:
    init(secret_key=_secret_key, algorithm=_algorithm)

__all__ = ["require_superuser", "SuperuserUser"]
