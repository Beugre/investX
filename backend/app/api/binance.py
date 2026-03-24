"""
Endpoints Binance : /binance/connect, /binance/validate, /binance/disconnect, /binance/status
"""

from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends

from app.core.auth_firebase import get_current_uid
from app.core.exceptions import BadRequest
from app.schemas.portfolio import BinanceConnectRequest, BinanceStatusResponse
from app.services import (
    binance_service,
    secret_manager_service,
    firestore_service,
    audit_service,
)
from app.logger import get_logger

logger = get_logger(__name__)
router = APIRouter(prefix="/binance", tags=["Binance"])


@router.post("/connect")
async def connect_binance(
    payload: BinanceConnectRequest,
    uid: str = Depends(get_current_uid),
):
    """Connecte un compte Binance : valide, vérifie permissions, stocke dans Secret Manager."""
    # 1. Valider les credentials
    valid = binance_service.validate_credentials(payload.api_key, payload.api_secret)
    if not valid:
        raise BadRequest("Invalid Binance credentials")

    # 2. Vérifier que pas de permission retrait
    safe = binance_service.check_no_withdraw_permission(
        payload.api_key, payload.api_secret
    )
    if not safe:
        raise BadRequest(
            "API key must NOT have withdrawal permission. "
            "Please create a trading-only API key."
        )

    # 3. Stocker dans Secret Manager
    secret_ref = secret_manager_service.create_or_update_binance_secret(
        uid, payload.api_key, payload.api_secret
    )

    # 4. Mettre à jour Firestore
    firestore_service.update_binance_account(
        uid,
        {
            "exchange": "binance",
            "secret_ref": secret_ref,
            "label": "Main Binance Account",
            "is_connected": True,
            "permissions_validated": True,
            "last_validation_at": datetime.now(timezone.utc),
        },
    )

    # 5. Audit
    audit_service.log_binance_connected(uid)

    return {"message": "Binance account connected successfully"}


@router.post("/validate")
async def validate_binance(uid: str = Depends(get_current_uid)):
    """Re-valide les credentials Binance existantes."""
    account = firestore_service.get_binance_account(uid)
    if not account or not account.get("is_connected"):
        raise BadRequest("Binance account not connected")

    try:
        creds = secret_manager_service.get_binance_secret(uid)
        valid = binance_service.validate_credentials(
            creds["api_key"], creds["api_secret"]
        )
        safe = binance_service.check_no_withdraw_permission(
            creds["api_key"], creds["api_secret"]
        )
    except Exception as e:
        firestore_service.update_binance_account(
            uid, {"permissions_validated": False}
        )
        raise BadRequest(f"Validation failed: {e}") from e

    firestore_service.update_binance_account(
        uid,
        {
            "permissions_validated": valid and safe,
            "last_validation_at": datetime.now(timezone.utc),
        },
    )

    return {
        "valid": valid,
        "safe": safe,
        "message": "OK" if (valid and safe) else "Validation issue detected",
    }


@router.delete("/disconnect")
async def disconnect_binance(uid: str = Depends(get_current_uid)):
    """Déconnecte le compte Binance et supprime le secret."""
    try:
        secret_manager_service.delete_binance_secret(uid)
    except Exception as e:
        logger.warning("Could not delete secret for user %s: %s", uid, e)

    firestore_service.delete_binance_account(uid)
    audit_service.log_binance_disconnected(uid)

    return {"message": "Binance account disconnected"}


@router.get("/status", response_model=BinanceStatusResponse)
async def get_binance_status(uid: str = Depends(get_current_uid)):
    """Retourne le statut de connexion Binance."""
    account = firestore_service.get_binance_account(uid)
    if not account:
        return BinanceStatusResponse()
    return BinanceStatusResponse(**account)
