"""
Service Google Secret Manager – gestion sécurisée des credentials Binance.
"""

from __future__ import annotations

import json

from google.cloud import secretmanager

from app.config import settings
from app.core.exceptions import SecretManagerError
from app.logger import get_logger

logger = get_logger(__name__)

_client: secretmanager.SecretManagerServiceClient | None = None


def _get_client() -> secretmanager.SecretManagerServiceClient:
    global _client
    if _client is None:
        _client = secretmanager.SecretManagerServiceClient()
    return _client


def _secret_name(uid: str) -> str:
    return f"binance-user-{uid}"


def _secret_path(uid: str) -> str:
    return f"projects/{settings.firebase_project_id}/secrets/{_secret_name(uid)}"


def create_or_update_binance_secret(uid: str, api_key: str, api_secret: str) -> str:
    """Crée ou met à jour le secret Binance pour un utilisateur.
    Retourne la référence au secret (secret_ref).
    """
    client = _get_client()
    project_path = f"projects/{settings.firebase_project_id}"
    secret_id = _secret_name(uid)
    payload = json.dumps({"api_key": api_key, "api_secret": api_secret}).encode("utf-8")

    try:
        # Essayer de créer le secret
        client.create_secret(
            request={
                "parent": project_path,
                "secret_id": secret_id,
                "secret": {"replication": {"automatic": {}}},
            }
        )
        logger.info("Secret created for user %s", uid)
    except Exception as e:
        if "ALREADY_EXISTS" in str(e):
            logger.info("Secret already exists for user %s, adding new version", uid)
        else:
            logger.error("Failed to create secret for user %s: %s", uid, e)
            raise SecretManagerError(f"Failed to create secret: {e}") from e

    try:
        # Ajouter une nouvelle version
        client.add_secret_version(
            request={
                "parent": _secret_path(uid),
                "payload": {"data": payload},
            }
        )
        secret_ref = f"{_secret_path(uid)}/versions/latest"
        logger.info("Secret version added for user %s", uid)
        return secret_ref
    except Exception as e:
        logger.error("Failed to add secret version for user %s: %s", uid, e)
        raise SecretManagerError(f"Failed to add secret version: {e}") from e


def get_binance_secret(uid: str) -> dict[str, str]:
    """Récupère les credentials Binance depuis Secret Manager.
    Retourne {"api_key": "...", "api_secret": "..."}.
    """
    client = _get_client()
    version_path = f"{_secret_path(uid)}/versions/latest"

    try:
        response = client.access_secret_version(request={"name": version_path})
        data = json.loads(response.payload.data.decode("utf-8"))
        return {"api_key": data["api_key"], "api_secret": data["api_secret"]}
    except Exception as e:
        logger.error("Failed to access secret for user %s: %s", uid, e)
        raise SecretManagerError(f"Failed to access secret: {e}") from e


def delete_binance_secret(uid: str) -> None:
    """Supprime le secret Binance d'un utilisateur."""
    client = _get_client()
    try:
        client.delete_secret(request={"name": _secret_path(uid)})
        logger.info("Secret deleted for user %s", uid)
    except Exception as e:
        logger.error("Failed to delete secret for user %s: %s", uid, e)
        raise SecretManagerError(f"Failed to delete secret: {e}") from e
