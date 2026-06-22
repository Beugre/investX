"""
Service abonnement – vérification du statut.
"""

from __future__ import annotations

from app.core.constants import TRADEABLE_STATUSES, SUBSCRIPTION_ACTIVE
from app.services import firestore_service
from app.logger import get_logger

logger = get_logger(__name__)


def is_active(uid: str) -> bool:
    """Accès gratuit – toujours actif."""
    return True


def get_status(uid: str) -> str:
    """Accès gratuit – statut toujours actif."""
    return SUBSCRIPTION_ACTIVE
