"""
Endpoints Admin : vue d'ensemble pour l'administrateur.
Protégé par une liste d'UIDs admin configurée via variable d'environnement.
"""

from __future__ import annotations

import os

from fastapi import APIRouter, Depends

from app.core.auth_firebase import get_current_uid
from app.core.exceptions import Forbidden
from app.services import firestore_service
from app.logger import get_logger

logger = get_logger(__name__)
router = APIRouter(prefix="/admin", tags=["Admin"])

ADMIN_UIDS: set[str] = set(
    uid.strip()
    for uid in os.getenv("ADMIN_UIDS", "").split(",")
    if uid.strip()
)


def _require_admin(uid: str = Depends(get_current_uid)) -> str:
    """Dependency : vérifie que l'utilisateur est admin."""
    if uid not in ADMIN_UIDS:
        raise Forbidden("Admin access required")
    return uid


@router.get("/overview")
async def admin_overview(uid: str = Depends(_require_admin)):
    """Vue d'ensemble : nombre d'utilisateurs, DCA actifs, ordres."""
    users = firestore_service.get_all_active_users()
    total_users = len(users)
    dca_v1_active = 0
    dca_v2_active = 0
    for user in users:
        u = user["uid"]
        cfg = firestore_service.get_dca_config(u)
        if cfg and cfg.get("enabled"):
            dca_v1_active += 1
        v2 = firestore_service.get_dca_v2_config(u)
        if v2 and v2.get("enabled"):
            dca_v2_active += 1

    return {
        "total_users": total_users,
        "dca_v1_active": dca_v1_active,
        "dca_v2_active": dca_v2_active,
    }


@router.get("/users")
async def admin_list_users(uid: str = Depends(_require_admin)):
    """Liste tous les utilisateurs avec leur statut."""
    users = firestore_service.get_all_active_users()
    result = []
    for user in users:
        u = user["uid"]
        cfg = firestore_service.get_dca_config(u)
        v2 = firestore_service.get_dca_v2_config(u)
        sub = firestore_service.get_subscription(u)
        result.append({
            "uid": u,
            "email": user.get("email", ""),
            "display_name": user.get("display_name", ""),
            "dca_v1_enabled": bool(cfg and cfg.get("enabled")),
            "dca_v2_enabled": bool(v2 and v2.get("enabled")),
            "subscription_plan": (sub or {}).get("plan", "free"),
            "subscription_status": (sub or {}).get("status", "none"),
        })
    return result


@router.get("/recent-orders")
async def admin_recent_orders(
    limit: int = 50,
    uid: str = Depends(_require_admin),
):
    """Derniers ordres de tous les utilisateurs (pour monitoring)."""
    users = firestore_service.get_all_active_users()
    all_orders = []
    for user in users:
        u = user["uid"]
        orders = firestore_service.list_orders(u, limit=5)
        for o in orders:
            o["uid"] = u
            o["email"] = user.get("email", "")
            all_orders.append(o)

    # Trier par date décroissante
    all_orders.sort(
        key=lambda x: x.get("created_at", ""),
        reverse=True,
    )
    return all_orders[:limit]
