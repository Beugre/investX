"""
Service de stockage sécurisé des credentials Binance.
Utilise Firestore + chiffrement Fernet (AES-128-CBC) au lieu de GCP Secret Manager.
La clé de chiffrement est définie via la variable d'environnement ENCRYPTION_KEY.
"""

from __future__ import annotations

import json
import os
import base64
import hashlib

from cryptography.fernet import Fernet

from app.core.exceptions import SecretManagerError
from app.logger import get_logger

logger = get_logger(__name__)

_fernet: Fernet | None = None


def _get_fernet() -> Fernet:
    """Initialise le chiffreur Fernet à partir de ENCRYPTION_KEY."""
    global _fernet
    if _fernet is None:
        raw_key = os.environ.get("ENCRYPTION_KEY", "")
        if not raw_key:
            # Auto-générer une clé déterministe à partir du project ID (fallback)
            from app.config import settings
            raw_key = settings.firebase_project_id + "-investx-secret-key"
            logger.warning("ENCRYPTION_KEY not set, using derived key (set it in .env for production)")
        # Dériver une clé Fernet valide (32 bytes base64) depuis n'importe quelle chaîne
        key_bytes = hashlib.sha256(raw_key.encode()).digest()
        fernet_key = base64.urlsafe_b64encode(key_bytes)
        _fernet = Fernet(fernet_key)
    return _fernet


def _get_firestore_db():
    """Récupère le client Firestore."""
    from app.services.firestore_service import _db
    return _db()


def create_or_update_binance_secret(uid: str, api_key: str, api_secret: str) -> str:
    """Chiffre et stocke les credentials Binance dans Firestore.
    Retourne une référence (secret_ref).
    """
    try:
        fernet = _get_fernet()
        payload = json.dumps({"api_key": api_key, "api_secret": api_secret})
        encrypted = fernet.encrypt(payload.encode("utf-8")).decode("utf-8")

        db = _get_firestore_db()
        doc_ref = db.collection("binance_secrets").document(uid)
        doc_ref.set({"encrypted_credentials": encrypted})

        secret_ref = f"firestore://binance_secrets/{uid}"
        logger.info("Binance credentials stored (encrypted) for user %s", uid)
        return secret_ref
    except Exception as e:
        logger.error("Failed to store Binance credentials for user %s: %s", uid, e)
        raise SecretManagerError(f"Failed to store credentials: {e}") from e


def get_binance_secret(uid: str) -> dict[str, str]:
    """Déchiffre et retourne les credentials Binance.
    Retourne {"api_key": "...", "api_secret": "..."}.
    """
    try:
        db = _get_firestore_db()
        doc = db.collection("binance_secrets").document(uid).get()
        if not doc.exists:
            raise SecretManagerError(f"No Binance credentials found for user {uid}")

        encrypted = doc.to_dict()["encrypted_credentials"]
        fernet = _get_fernet()
        decrypted = fernet.decrypt(encrypted.encode("utf-8")).decode("utf-8")
        data = json.loads(decrypted)
        return {"api_key": data["api_key"], "api_secret": data["api_secret"]}
    except SecretManagerError:
        raise
    except Exception as e:
        logger.error("Failed to retrieve Binance credentials for user %s: %s", uid, e)
        raise SecretManagerError(f"Failed to retrieve credentials: {e}") from e


def delete_binance_secret(uid: str) -> None:
    """Supprime les credentials Binance chiffrées."""
    try:
        db = _get_firestore_db()
        db.collection("binance_secrets").document(uid).delete()
        logger.info("Binance credentials deleted for user %s", uid)
    except Exception as e:
        logger.error("Failed to delete Binance credentials for user %s: %s", uid, e)
        raise SecretManagerError(f"Failed to delete credentials: {e}") from e
