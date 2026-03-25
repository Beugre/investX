"""
Endpoints Revolut X : /revolutx/connect, /revolutx/validate, /revolutx/disconnect, /revolutx/status
"""

from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends

from app.core.auth_firebase import get_current_uid
from app.core.exceptions import BadRequest
from app.schemas.portfolio import RevolutXConnectRequest, RevolutXStatusResponse
from app.services import (
    revolutx_service,
    secret_manager_service,
    firestore_service,
    audit_service,
)
from app.logger import get_logger

logger = get_logger(__name__)
router = APIRouter(prefix="/revolutx", tags=["RevolutX"])


@router.post("/connect")
async def connect_revolutx(
    payload: RevolutXConnectRequest,
    uid: str = Depends(get_current_uid),
):
    """Connecte un compte Revolut X : valide les credentials, stocke dans Secret Manager."""
    # 1. Valider les credentials
    valid = revolutx_service.validate_credentials(payload.api_key, payload.private_key_pem)
    if not valid:
        raise BadRequest("Invalid Revolut X credentials")

    # 2. Stocker dans Secret Manager
    secret_ref = secret_manager_service.create_or_update_revolutx_secret(
        uid, payload.api_key, payload.private_key_pem
    )

    # 3. Mettre à jour Firestore
    firestore_service.update_revolutx_account(
        uid,
        {
            "exchange": "revolutx",
            "secret_ref": secret_ref,
            "label": "Main Revolut X Account",
            "is_connected": True,
            "permissions_validated": True,
            "last_validation_at": datetime.now(timezone.utc),
        },
    )

    # 4. Définir comme exchange actif
    firestore_service.set_active_exchange(uid, "revolutx")

    # 5. Audit
    audit_service.log_revolutx_connected(uid)

    return {"message": "Revolut X account connected successfully"}


@router.post("/validate")
async def validate_revolutx(uid: str = Depends(get_current_uid)):
    """Re-valide les credentials Revolut X existantes."""
    account = firestore_service.get_revolutx_account(uid)
    if not account or not account.get("is_connected"):
        raise BadRequest("Revolut X account not connected")

    try:
        creds = secret_manager_service.get_revolutx_secret(uid)
        valid = revolutx_service.validate_credentials(
            creds["api_key"], creds["private_key_pem"]
        )
    except Exception as e:
        firestore_service.update_revolutx_account(
            uid, {"permissions_validated": False}
        )
        raise BadRequest(f"Validation failed: {e}") from e

    firestore_service.update_revolutx_account(
        uid,
        {
            "permissions_validated": valid,
            "last_validation_at": datetime.now(timezone.utc),
        },
    )

    return {
        "valid": valid,
        "safe": True,  # Revolut X n'a pas de permission de retrait
        "message": "OK" if valid else "Validation issue detected",
    }


@router.delete("/disconnect")
async def disconnect_revolutx(uid: str = Depends(get_current_uid)):
    """Déconnecte le compte Revolut X et supprime le secret."""
    try:
        secret_manager_service.delete_revolutx_secret(uid)
    except Exception as e:
        logger.warning("Could not delete Revolut X secret for user %s: %s", uid, e)

    firestore_service.delete_revolutx_account(uid)

    # Si l'exchange actif était revolutx, revenir à binance
    if firestore_service.get_active_exchange(uid) == "revolutx":
        firestore_service.set_active_exchange(uid, "binance")

    audit_service.log_revolutx_disconnected(uid)

    return {"message": "Revolut X account disconnected"}


@router.get("/status", response_model=RevolutXStatusResponse)
async def get_revolutx_status(uid: str = Depends(get_current_uid)):
    """Retourne le statut de connexion Revolut X."""
    account = firestore_service.get_revolutx_account(uid)
    if not account:
        return RevolutXStatusResponse()
    return RevolutXStatusResponse(**account)
