"""
Schémas Pydantic – Stripe / Abonnement.
"""

from __future__ import annotations

from datetime import datetime
from pydantic import BaseModel


class SubscriptionStatus(BaseModel):
    provider: str = "stripe"
    customer_id: str | None = None
    subscription_id: str | None = None
    status: str = "none"
    price_id: str | None = None
    current_period_end: datetime | None = None
    cancel_at_period_end: bool = False


class CheckoutSessionResponse(BaseModel):
    checkout_url: str


class CustomerPortalResponse(BaseModel):
    portal_url: str
