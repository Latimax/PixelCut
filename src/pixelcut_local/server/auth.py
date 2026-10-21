"""Authentication and security token verification for LAN mobile clients."""

from __future__ import annotations

import logging
import secrets
from typing import Optional
from fastapi import HTTPException, Request, Security, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from pixelcut_local.config import Settings

logger = logging.getLogger(__name__)
security_bearer = HTTPBearer(auto_error=False)


def verify_client_access(request: Request, credentials: Optional[HTTPAuthorizationCredentials] = Security(security_bearer)) -> bool:
    """Verify incoming client request authorization.

    Localhost clients (127.0.0.1, ::1) are allowed freely for local desktop integration.
    Remote LAN clients must provide the configured pairing token when LAN mode is active.
    """
    settings = Settings.load()

    client_ip = request.client.host if request.client else "unknown"
    is_localhost = client_ip in ("127.0.0.1", "::1", "localhost", "testclient")

    # If LAN mode is disabled, forbid non-localhost requests outright
    if not settings.lan_mode_enabled and not is_localhost:
        logger.warning("Rejected non-localhost request from %s while LAN mode is disabled", client_ip)
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="LAN access is disabled on this server. Enable LAN mode in Desktop Settings to allow mobile connections.",
        )

    # If request is from localhost and LAN mode is off, allow immediately
    if is_localhost and not settings.lan_mode_enabled:
        return True



    # If LAN mode is active, check required pairing token
    configured_token = settings.pairing_token.strip()
    if not configured_token:
        # If no token set, allow local connections
        if is_localhost:
            return True
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Server pairing token is not configured.",
        )

    # Check Bearer token or custom header X-Pairing-Token
    provided_token = ""
    if credentials and credentials.credentials:
        provided_token = credentials.credentials.strip()
    elif "x-pairing-token" in request.headers:
        provided_token = request.headers["x-pairing-token"].strip()

    if not provided_token or not secrets.compare_digest(provided_token, configured_token):
        logger.warning("Unauthorized access attempt from client IP %s", client_ip)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing pairing token.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return True
