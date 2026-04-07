"""
Endpoints utilisateur : /me, /onboarding/init
"""

from __future__ import annotations

from fastapi import APIRouter, Depends
from firebase_admin import auth as firebase_auth

from app.core.auth_firebase import get_current_uid
from app.core.exceptions import NotFound, BadRequest
from pydantic import BaseModel
from app.schemas.user import UserProfile, OnboardingResponse
from app.services import firestore_service, email_service, binance_service, revolutx_service, secret_manager_service
from app.logger import get_logger

logger = get_logger(__name__)

router = APIRouter(tags=["Users"])


@router.get("/me", response_model=UserProfile)
async def get_me(uid: str = Depends(get_current_uid)):
    """Retourne le profil de l'utilisateur connecté."""
    user = firestore_service.get_user(uid)
    if not user:
        raise NotFound("User profile not found")
    return UserProfile(**user)


@router.post("/onboarding/init", response_model=OnboardingResponse)
async def init_onboarding(uid: str = Depends(get_current_uid)):
    """Initialise le profil utilisateur dans Firestore (première connexion)."""
    existing = firestore_service.get_user(uid)
    if existing:
        return OnboardingResponse(uid=uid, message="User already exists")

    # Récupérer l'email depuis Firebase Auth
    try:
        firebase_user = firebase_auth.get_user(uid)
        email = firebase_user.email or ""
        display_name = firebase_user.display_name or ""
    except Exception:
        email = ""
        display_name = ""

    firestore_service.create_user(
        uid,
        {
            "email": email,
            "display_name": display_name,
            "timezone": "Europe/Paris",
        },
    )
    # Email de bienvenue (fire-and-forget)
    try:
        email_service.send_welcome_email(email, display_name)
    except Exception:
        pass  # Ne pas bloquer l'onboarding en cas d'échec email

    return OnboardingResponse(uid=uid, message="User initialized")


@router.get("/me/profile", response_model=UserProfile)
async def get_profile(uid: str = Depends(get_current_uid)):
    """Alias de /me pour compatibilité."""
    user = firestore_service.get_user(uid)
    if not user:
        raise NotFound("User profile not found")
    return UserProfile(**user)


class UpdateProfileRequest(BaseModel):
    display_name: str | None = None
    timezone: str | None = None


@router.put("/me/profile", response_model=UserProfile)
async def update_profile(
    body: UpdateProfileRequest,
    uid: str = Depends(get_current_uid),
):
    """Met à jour le profil utilisateur (display_name, timezone)."""
    user = firestore_service.get_user(uid)
    if not user:
        raise NotFound("User profile not found")

    updates = {}
    if body.display_name is not None:
        updates["display_name"] = body.display_name
    if body.timezone is not None:
        updates["timezone"] = body.timezone

    if updates:
        firestore_service.update_user(uid, updates)

    user = firestore_service.get_user(uid)
    return UserProfile(**user)


# ── Active Exchange ──

@router.get("/me/exchange")
async def get_active_exchange(uid: str = Depends(get_current_uid)):
    """Retourne l'exchange actif de l'utilisateur."""
    exchange = firestore_service.get_active_exchange(uid)
    return {"active_exchange": exchange}


class SetExchangeRequest(BaseModel):
    exchange: str


@router.put("/me/exchange")
async def set_active_exchange(
    body: SetExchangeRequest,
    uid: str = Depends(get_current_uid),
):
    """Définit l'exchange actif."""
    from app.core.constants import SUPPORTED_EXCHANGES
    if body.exchange not in SUPPORTED_EXCHANGES:
        raise BadRequest(f"Exchange '{body.exchange}' not supported. Valid: {SUPPORTED_EXCHANGES}")
    firestore_service.set_active_exchange(uid, body.exchange)
    return {"active_exchange": body.exchange}


# ── Balance exchange ──

@router.get("/me/balance")
async def get_balance(uid: str = Depends(get_current_uid)):
    """Retourne les balances USDC et EUR (et autres stables) de l'exchange actif."""
    exchange = firestore_service.get_active_exchange(uid)

    try:
        if exchange == "revolutx":
            account = firestore_service.get_revolutx_account(uid)
            if not account or not account.get("is_connected"):
                return {"exchange": exchange, "balances": {}, "error": "Exchange not connected"}
            creds = secret_manager_service.get_revolutx_secret(uid)
            raw = revolutx_service.get_asset_balances(
                api_key=creds["api_key"],
                private_key_pem=creds["private_key_pem"],
                assets=["EUR", "USDC"],
            )
        else:
            account = firestore_service.get_binance_account(uid)
            if not account or not account.get("is_connected"):
                return {"exchange": exchange, "balances": {}, "error": "Exchange not connected"}
            creds = secret_manager_service.get_binance_secret(uid)
            raw = binance_service.get_asset_balances(
                api_key=creds["api_key"],
                api_secret=creds["api_secret"],
                assets=["USDC", "EUR"],
            )
        return {"exchange": exchange, "balances": raw}
    except Exception as e:
        logger.warning("Failed to fetch balance for user %s: %s", uid, e)
        return {"exchange": exchange, "balances": {}, "error": str(e)}
