"""
Endpoints internes (admin) : déclenchement manuel du cycle DCA, refresh snapshots, etc.
Protégés par authentification admin.
"""

from __future__ import annotations

import os

from fastapi import APIRouter, Depends

from app.core.auth_firebase import get_current_uid
from app.core.exceptions import Forbidden
from app.services import dca_service, portfolio_service, firestore_service
from app.logger import get_logger

logger = get_logger(__name__)
router = APIRouter(prefix="/internal", tags=["Internal"])

_ADMIN_UIDS: set[str] = set(
    uid.strip()
    for uid in os.getenv("ADMIN_UIDS", "").split(",")
    if uid.strip()
)


def _require_admin(uid: str = Depends(get_current_uid)) -> str:
    if uid not in _ADMIN_UIDS:
        raise Forbidden("Admin access required")
    return uid


@router.post("/run-dca-cycle")
async def run_dca_cycle(uid: str = Depends(_require_admin)):
    """Exécute un cycle DCA manuellement (admin uniquement)."""
    executed = dca_service.run_cycle()
    return {"executed_orders": executed}


@router.post("/refresh-snapshots")
async def refresh_all_snapshots(admin_uid: str = Depends(_require_admin)):
    """Recalcule les snapshots pour tous les utilisateurs actifs (v1 + v2)."""
    from app.scheduler.jobs import portfolio_refresh_job
    portfolio_refresh_job()
    return {"status": "ok"}


@router.post("/reconcile-subscriptions")
async def reconcile_subscriptions(uid: str = Depends(_require_admin)):
    """Réconciliation basique : vérifie la cohérence des abonnements.
    En MVP, juste un check de santé.
    """
    users = firestore_service.get_all_active_users()
    issues = []
    for user in users:
        uid = user["uid"]
        sub = firestore_service.get_subscription(uid)
        if not sub:
            issues.append({"uid": uid, "issue": "no_subscription_record"})
    return {"total_users": len(users), "issues": issues}
