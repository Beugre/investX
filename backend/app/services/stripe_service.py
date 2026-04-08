"""
Service Stripe – Checkout, Customer Portal et Webhook.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import stripe

from app.config import settings
from app.logger import get_logger
from app.services import firestore_service

logger = get_logger(__name__)

stripe.api_key = settings.stripe_secret_key


# ────────────────────── Checkout ──────────────────────

def create_checkout_session(uid: str, email: str) -> str:
    """Crée une session Stripe Checkout et retourne l'URL."""
    session = stripe.checkout.Session.create(
        mode="subscription",
        customer_email=email,
        line_items=[{"price": settings.stripe_price_id, "quantity": 1}],
        success_url=settings.stripe_success_url,
        cancel_url=settings.stripe_cancel_url,
        metadata={"firebase_uid": uid},
    )
    logger.info("Checkout session created for user %s: %s", uid, session.id)
    return session.url  # type: ignore[return-value]


# ────────────────────── Customer Portal ──────────────────────

def create_customer_portal_session(customer_id: str) -> str:
    """Crée une session Customer Portal Stripe et retourne l'URL."""
    session = stripe.billing_portal.Session.create(
        customer=customer_id,
        return_url=settings.stripe_success_url,
    )
    return session.url  # type: ignore[return-value]


# ────────────────────── Webhook ──────────────────────

def verify_webhook_signature(payload: bytes, signature: str) -> dict[str, Any]:
    """Vérifie la signature du webhook Stripe et retourne l'événement."""
    event = stripe.Webhook.construct_event(
        payload, signature, settings.stripe_webhook_secret
    )
    return event  # type: ignore[return-value]


def handle_event(event: dict[str, Any]) -> None:
    """Traite un événement Stripe webhook (avec idempotency)."""
    event_type = event["type"]
    event_id = event["id"]
    data_object = event["data"]["object"]

    logger.info("Handling Stripe event: %s (%s)", event_type, event_id)

    # Idempotency: skip si déjà traité
    db = firestore_service._db()
    event_ref = db.collection("stripe_events").document(event_id)
    if event_ref.get().exists:
        logger.info("Stripe event %s already processed, skipping", event_id)
        return
    event_ref.set({"type": event_type, "processed_at": datetime.now(timezone.utc)})

    if event_type == "checkout.session.completed":
        _handle_checkout_completed(data_object)
    elif event_type in (
        "customer.subscription.created",
        "customer.subscription.updated",
    ):
        _handle_subscription_updated(data_object, event["id"])
    elif event_type == "customer.subscription.deleted":
        _handle_subscription_deleted(data_object, event["id"])
    elif event_type == "invoice.paid":
        _handle_invoice_paid(data_object)
    elif event_type == "invoice.payment_failed":
        _handle_invoice_payment_failed(data_object)
    else:
        logger.info("Unhandled Stripe event type: %s", event_type)


def _find_uid_by_customer_id(customer_id: str) -> str | None:
    """Cherche le uid Firebase associé à un customer_id Stripe.
    Utilise d'abord l'index stripe_customers pour un lookup O(1),
    puis fallback sur le scan complet.
    """
    db = firestore_service._db()

    # 1. Lookup rapide via l'index
    idx_doc = db.collection("stripe_customers").document(customer_id).get()
    if idx_doc.exists:
        uid = idx_doc.to_dict().get("uid")
        if uid:
            return uid

    # 2. Fallback : scan (legacy, sera de moins en moins utilisé)
    docs = db.collection("users").stream()
    for doc in docs:
        sub = (
            db.collection("users")
            .document(doc.id)
            .collection("subscription")
            .document("main")
            .get()
        )
        if sub.exists and sub.to_dict().get("customer_id") == customer_id:
            # Écrire l'index pour les prochains appels
            db.collection("stripe_customers").document(customer_id).set(
                {"uid": doc.id, "created_at": datetime.now(timezone.utc)}
            )
            return doc.id
    return None


def _handle_checkout_completed(session: dict[str, Any]) -> None:
    uid = session.get("metadata", {}).get("firebase_uid")
    if not uid:
        logger.warning("Checkout completed without firebase_uid in metadata")
        return

    customer_id = session.get("customer")
    subscription_id = session.get("subscription")

    firestore_service.update_subscription(
        uid,
        {
            "provider": "stripe",
            "customer_id": customer_id,
            "subscription_id": subscription_id,
            "status": "active",
            "price_id": settings.stripe_price_id,
        },
    )
    logger.info("Checkout completed for user %s", uid)


def _handle_subscription_updated(sub: dict[str, Any], event_id: str) -> None:
    customer_id = sub.get("customer")
    uid = _find_uid_by_customer_id(customer_id)
    if not uid:
        logger.warning("No user found for customer %s", customer_id)
        return

    period_end = sub.get("current_period_end")
    firestore_service.update_subscription(
        uid,
        {
            "status": sub.get("status", "unknown"),
            "subscription_id": sub.get("id"),
            "cancel_at_period_end": sub.get("cancel_at_period_end", False),
            "current_period_end": (
                datetime.fromtimestamp(period_end, tz=timezone.utc)
                if period_end
                else None
            ),
            "last_event_id": event_id,
        },
    )


def _handle_subscription_deleted(sub: dict[str, Any], event_id: str) -> None:
    customer_id = sub.get("customer")
    uid = _find_uid_by_customer_id(customer_id)
    if not uid:
        logger.warning("No user found for customer %s", customer_id)
        return

    firestore_service.update_subscription(
        uid,
        {
            "status": "canceled",
            "last_event_id": event_id,
        },
    )
    logger.info("Subscription canceled for user %s", uid)


def _handle_invoice_paid(invoice: dict[str, Any]) -> None:
    customer_id = invoice.get("customer")
    uid = _find_uid_by_customer_id(customer_id)
    if uid:
        logger.info("Invoice paid for user %s", uid)


def _handle_invoice_payment_failed(invoice: dict[str, Any]) -> None:
    customer_id = invoice.get("customer")
    uid = _find_uid_by_customer_id(customer_id)
    if not uid:
        return

    firestore_service.update_subscription(uid, {"status": "past_due"})
    logger.warning("Invoice payment failed for user %s", uid)
