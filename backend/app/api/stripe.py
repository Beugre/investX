"""
Endpoints Stripe : checkout, portal, webhook, status
"""

from __future__ import annotations

from datetime import datetime, timezone

import stripe as stripe_lib
from fastapi import APIRouter, Depends, Request, HTTPException

from app.config import settings
from app.core.auth_firebase import get_current_uid
from app.core.exceptions import NotFound
from app.schemas.stripe import (
    CheckoutSessionResponse,
    CustomerPortalResponse,
    SubscriptionStatus,
)
from app.services import firestore_service, stripe_service
from app.logger import get_logger

try:
    from firebase_admin import auth as firebase_auth
except ImportError:
    firebase_auth = None  # type: ignore

logger = get_logger(__name__)
router = APIRouter(prefix="/billing", tags=["Billing"])


@router.post("/create-checkout-session", response_model=CheckoutSessionResponse)
async def create_checkout(uid: str = Depends(get_current_uid)):
    """Crée une session Stripe Checkout pour l'abonnement."""
    user = firestore_service.get_user(uid)

    # Auto-créer le profil si absent (onboarding raté)
    if not user:
        email = ""
        try:
            if firebase_auth:
                fb_user = firebase_auth.get_user(uid)
                email = fb_user.email or ""
        except Exception:
            pass
        firestore_service.create_user(uid, {"email": email, "display_name": "", "timezone": "Europe/Paris"})
        user = firestore_service.get_user(uid) or {"email": email}

    email = user.get("email", "")
    url = stripe_service.create_checkout_session(uid, email)
    return CheckoutSessionResponse(checkout_url=url)


@router.post(
    "/create-customer-portal-session", response_model=CustomerPortalResponse
)
async def create_portal(uid: str = Depends(get_current_uid)):
    """Crée une session Customer Portal Stripe."""
    sub = firestore_service.get_subscription(uid)
    if not sub or not sub.get("customer_id"):
        raise NotFound("No active subscription found")

    url = stripe_service.create_customer_portal_session(sub["customer_id"])
    return CustomerPortalResponse(portal_url=url)


@router.post("/webhook")
async def stripe_webhook(request: Request):
    """Réceptionne et traite les webhooks Stripe.
    NB : Pas d'auth Firebase ici – authentifié par la signature Stripe.
    """
    payload = await request.body()
    sig_header = request.headers.get("stripe-signature", "")

    try:
        event = stripe_service.verify_webhook_signature(payload, sig_header)
    except Exception as e:
        logger.warning("Invalid Stripe webhook signature: %s", e)
        raise HTTPException(status_code=400, detail="Invalid signature") from e

    stripe_service.handle_event(event)
    return {"received": True}


@router.get("/status", response_model=SubscriptionStatus)
async def get_subscription_status(uid: str = Depends(get_current_uid)):
    """Retourne le statut de l'abonnement."""
    sub = firestore_service.get_subscription(uid)
    if not sub:
        return SubscriptionStatus()
    return SubscriptionStatus(**sub)


@router.post("/sync", response_model=SubscriptionStatus)
async def sync_subscription(uid: str = Depends(get_current_uid)):
    """Synchronise le statut d'abonnement depuis l'API Stripe.

    Utile en développement local sans webhook Stripe.
    Recherche les checkout sessions récentes et met à jour Firestore.
    """
    # Déjà actif ?
    sub = firestore_service.get_subscription(uid)
    if sub and sub.get("status") == "active":
        return SubscriptionStatus(**sub)

    # Chercher dans les checkout sessions récentes
    try:
        sessions = stripe_lib.checkout.Session.list(limit=20)
        for sess in sessions.data:
            if (
                sess.metadata.get("firebase_uid") == uid
                and sess.status == "complete"
                and sess.subscription
            ):
                subscription = stripe_lib.Subscription.retrieve(sess.subscription)
                sub_data = {
                    "provider": "stripe",
                    "customer_id": sess.customer,
                    "subscription_id": str(sess.subscription),
                    "status": subscription.status,
                    "price_id": settings.stripe_price_id,
                    "cancel_at_period_end": getattr(
                        subscription, "cancel_at_period_end", False
                    ),
                }
                if subscription.current_period_end:
                    sub_data["current_period_end"] = datetime.fromtimestamp(
                        subscription.current_period_end, tz=timezone.utc
                    )
                firestore_service.update_subscription(uid, sub_data)
                logger.info("Subscription synced for user %s: %s", uid, subscription.status)
                return SubscriptionStatus(**sub_data)
    except Exception as e:
        logger.error("Failed to sync subscription from Stripe: %s", e)

    return SubscriptionStatus()
