"""
Middleware d'authentification Firebase.
Vérifie le token Firebase et extrait le uid.
"""

from __future__ import annotations

from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from firebase_admin import auth as firebase_auth

from app.core.exceptions import NotAuthenticated
from app.logger import get_logger

logger = get_logger(__name__)
_bearer_scheme = HTTPBearer(auto_error=False)


async def get_current_uid(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer_scheme),
) -> str:
    """Dependency FastAPI : retourne le uid Firebase depuis le Bearer token."""
    if credentials is None:
        raise NotAuthenticated("Missing authorization header")

    token = credentials.credentials
    try:
        decoded = firebase_auth.verify_id_token(token)
        uid: str = decoded["uid"]
        return uid
    except Exception as exc:
        logger.warning("Firebase token verification failed: %s", exc)
        raise NotAuthenticated("Invalid or expired token") from exc
