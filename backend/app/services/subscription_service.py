"""
Service abonnement – vérification du statut.
"""

from __future__ import annotations

from app.core.constants import TRADEABLE_STATUSES
from app.services import firestore_service
from app.logger import get_logger

logger = get_logger(__name__)


def is_active(uid: str) -> bool:
    """Vérifie si l'abonnement de l'utilisateur est actif (trading autorisé)."""
    sub = firestore_service.get_subscription(uid)
    if not sub:
        return False
    status = sub.get("status", "none")
    return status in TRADEABLE_STATUSES


def get_status(uid: str) -> str:
    """Retourne le statut brut de l'abonnement."""
    sub = firestore_service.get_subscription(uid)
    if not sub:
        return "none"
    return sub.get("status", "none")
