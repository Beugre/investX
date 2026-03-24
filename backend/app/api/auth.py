"""
Endpoints internes (admin) : déclenchement manuel du cycle DCA, refresh snapshots, etc.
Ces endpoints doivent être protégés en production (IP whitelist, token interne, etc.)
"""

from __future__ import annotations

from fastapi import APIRouter

from app.services import dca_service, portfolio_service, firestore_service
from app.logger import get_logger

logger = get_logger(__name__)
router = APIRouter(prefix="/internal", tags=["Internal"])


@router.post("/run-dca-cycle")
async def run_dca_cycle():
    """Exécute un cycle DCA manuellement (debug / cron externe)."""
    executed = dca_service.run_cycle()
    return {"executed_orders": executed}


@router.post("/refresh-snapshots")
async def refresh_all_snapshots():
    """Recalcule les snapshots pour tous les utilisateurs actifs."""
    users = firestore_service.get_all_active_users()
    refreshed = 0
    for user in users:
        uid = user["uid"]
        config = firestore_service.get_dca_config(uid)
        if not config:
            continue
        symbol = config.get("symbol", "BTCUSDC")
        try:
            portfolio_service.refresh_snapshot(uid, symbol)
            refreshed += 1
        except Exception as e:
            logger.warning("Snapshot refresh failed for %s: %s", uid, e)

    return {"refreshed": refreshed}


@router.post("/reconcile-subscriptions")
async def reconcile_subscriptions():
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
