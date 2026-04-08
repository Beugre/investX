"""
Service Firestore – CRUD centralisé pour toutes les collections.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from google.cloud.firestore_v1 import FieldFilter
from google.cloud.firestore_v1 import Client as _FSClient
from firebase_admin import firestore as fb_firestore

from app.config import settings
from app.logger import get_logger

logger = get_logger(__name__)

# Cache du client Firestore
_firestore_client = None


def _db():
    """Retourne le client Firestore (avec database='default' explicite)."""
    global _firestore_client
    if _firestore_client is None:
        # firebase_admin utilise "(default)" comme database ID, mais certains
        # projets Firebase récents créent la base sous le nom "default" (sans
        # parenthèses). On utilise le client google-cloud-firestore directement
        # pour pouvoir spécifier database='default'.
        base_client = fb_firestore.client()
        _firestore_client = _FSClient(
            project=base_client.project,
            credentials=base_client._credentials,
            database="default",
        )
    return _firestore_client


# ────────────────────── Users ──────────────────────

def get_user(uid: str) -> dict[str, Any] | None:
    doc = _db().collection("users").document(uid).get()
    return doc.to_dict() if doc.exists else None


def create_user(uid: str, data: dict[str, Any]) -> None:
    now = datetime.now(timezone.utc)
    data.setdefault("created_at", now)
    data.setdefault("updated_at", now)
    data.setdefault("is_active", True)
    data.setdefault("role", "user")
    data["uid"] = uid
    _db().collection("users").document(uid).set(data)
    logger.info("User created: %s", uid)


def update_user(uid: str, data: dict[str, Any]) -> None:
    data["updated_at"] = datetime.now(timezone.utc)
    _db().collection("users").document(uid).update(data)


# ────────────────────── Subscription ──────────────────────

def get_subscription(uid: str) -> dict[str, Any] | None:
    doc = (
        _db()
        .collection("users")
        .document(uid)
        .collection("subscription")
        .document("main")
        .get()
    )
    return doc.to_dict() if doc.exists else None


def update_subscription(uid: str, data: dict[str, Any]) -> None:
    data["updated_at"] = datetime.now(timezone.utc)
    (
        _db()
        .collection("users")
        .document(uid)
        .collection("subscription")
        .document("main")
        .set(data, merge=True)
    )
    logger.info("Subscription updated for user %s: status=%s", uid, data.get("status"))


# ────────────────────── DCA Config ──────────────────────

def get_dca_config(uid: str) -> dict[str, Any] | None:
    doc = (
        _db()
        .collection("users")
        .document(uid)
        .collection("dca_config")
        .document("main")
        .get()
    )
    return doc.to_dict() if doc.exists else None


def update_dca_config(uid: str, data: dict[str, Any]) -> None:
    data["updated_at"] = datetime.now(timezone.utc)
    (
        _db()
        .collection("users")
        .document(uid)
        .collection("dca_config")
        .document("main")
        .set(data, merge=True)
    )
    logger.info("DCA config updated for user %s", uid)


# ────────────────────── Binance Account ──────────────────────

def get_binance_account(uid: str) -> dict[str, Any] | None:
    doc = (
        _db()
        .collection("users")
        .document(uid)
        .collection("binance_account")
        .document("main")
        .get()
    )
    return doc.to_dict() if doc.exists else None


def update_binance_account(uid: str, data: dict[str, Any]) -> None:
    data["updated_at"] = datetime.now(timezone.utc)
    (
        _db()
        .collection("users")
        .document(uid)
        .collection("binance_account")
        .document("main")
        .set(data, merge=True)
    )


def delete_binance_account(uid: str) -> None:
    (
        _db()
        .collection("users")
        .document(uid)
        .collection("binance_account")
        .document("main")
        .delete()
    )
    logger.info("Binance account deleted for user %s", uid)


# ────────────────────── Revolut X Account ──────────────────────

def get_revolutx_account(uid: str) -> dict[str, Any] | None:
    doc = (
        _db()
        .collection("users")
        .document(uid)
        .collection("revolutx_account")
        .document("main")
        .get()
    )
    return doc.to_dict() if doc.exists else None


def update_revolutx_account(uid: str, data: dict[str, Any]) -> None:
    data["updated_at"] = datetime.now(timezone.utc)
    (
        _db()
        .collection("users")
        .document(uid)
        .collection("revolutx_account")
        .document("main")
        .set(data, merge=True)
    )


def delete_revolutx_account(uid: str) -> None:
    (
        _db()
        .collection("users")
        .document(uid)
        .collection("revolutx_account")
        .document("main")
        .delete()
    )
    logger.info("Revolut X account deleted for user %s", uid)


# ────────────────────── Active Exchange ──────────────────────

def get_active_exchange(uid: str) -> str:
    """Retourne l'exchange actif de l'utilisateur ('binance' ou 'revolutx')."""
    user = get_user(uid)
    if not user:
        return "binance"
    return user.get("active_exchange", "binance")


def set_active_exchange(uid: str, exchange: str) -> None:
    """Définit l'exchange actif de l'utilisateur."""
    update_user(uid, {"active_exchange": exchange})
    logger.info("Active exchange set to '%s' for user %s", exchange, uid)


# ────────────────────── Telegram ──────────────────────

def get_telegram_settings(uid: str) -> dict[str, Any] | None:
    doc = (
        _db()
        .collection("users")
        .document(uid)
        .collection("telegram")
        .document("main")
        .get()
    )
    return doc.to_dict() if doc.exists else None


def update_telegram_settings(uid: str, data: dict[str, Any]) -> None:
    data["updated_at"] = datetime.now(timezone.utc)
    (
        _db()
        .collection("users")
        .document(uid)
        .collection("telegram")
        .document("main")
        .set(data, merge=True)
    )


# ────────────────────── Orders ──────────────────────

def save_order(uid: str, order_data: dict[str, Any]) -> str:
    ref = (
        _db()
        .collection("users")
        .document(uid)
        .collection("orders")
        .document()
    )
    order_data["created_at"] = datetime.now(timezone.utc)
    ref.set(order_data)
    logger.info("Order saved for user %s: %s", uid, ref.id)
    return ref.id


def list_orders(
    uid: str, limit: int = 50, symbol: str | None = None
) -> list[dict[str, Any]]:
    query = (
        _db()
        .collection("users")
        .document(uid)
        .collection("orders")
    )
    if symbol:
        query = query.where(filter=FieldFilter("symbol", "==", symbol))
    docs = query.order_by("executed_at", direction="DESCENDING").limit(limit).stream()
    return [{"order_id": d.id, **d.to_dict()} for d in docs]


def get_latest_order(uid: str, symbol: str) -> dict[str, Any] | None:
    docs = (
        _db()
        .collection("users")
        .document(uid)
        .collection("orders")
        .where(filter=FieldFilter("symbol", "==", symbol))
        .order_by("executed_at", direction="DESCENDING")
        .limit(1)
        .stream()
    )
    for d in docs:
        return {"order_id": d.id, **d.to_dict()}
    return None


# ────────────────────── Portfolio Snapshots ──────────────────────

def save_snapshot(uid: str, data: dict[str, Any]) -> str:
    ref = (
        _db()
        .collection("users")
        .document(uid)
        .collection("portfolio_snapshots")
        .document()
    )
    data["captured_at"] = datetime.now(timezone.utc)
    ref.set(data)

    # Garder uniquement les 100 derniers snapshots
    _prune_old_snapshots(uid, max_keep=100)

    return ref.id


def _prune_old_snapshots(uid: str, max_keep: int = 100) -> None:
    """Supprime les snapshots au-delà des `max_keep` plus récents."""
    coll = (
        _db()
        .collection("users")
        .document(uid)
        .collection("portfolio_snapshots")
    )
    # Récupérer tous les snapshots triés du plus récent au plus ancien
    all_docs = list(
        coll.order_by("captured_at", direction="DESCENDING")
        .offset(max_keep)
        .limit(500)
        .stream()
    )
    if not all_docs:
        return
    batch = _db().batch()
    for doc in all_docs:
        batch.delete(doc.reference)
    batch.commit()
    logger.info("Pruned %d old snapshots for user %s", len(all_docs), uid)


def get_latest_snapshot(uid: str, symbol: str) -> dict[str, Any] | None:
    docs = (
        _db()
        .collection("users")
        .document(uid)
        .collection("portfolio_snapshots")
        .where(filter=FieldFilter("symbol", "==", symbol))
        .order_by("captured_at", direction="DESCENDING")
        .limit(1)
        .stream()
    )
    for d in docs:
        return {"snapshot_id": d.id, **d.to_dict()}
    return None


def list_snapshots(
    uid: str, symbol: str | None = None, limit: int = 30
) -> list[dict[str, Any]]:
    query = (
        _db()
        .collection("users")
        .document(uid)
        .collection("portfolio_snapshots")
    )
    if symbol:
        query = query.where(filter=FieldFilter("symbol", "==", symbol))
    docs = query.order_by("captured_at", direction="DESCENDING").limit(limit).stream()
    return [{"snapshot_id": d.id, **d.to_dict()} for d in docs]


# ────────────────────── Audit Logs ──────────────────────

def save_audit_log(uid: str, action: str, status: str, message: str, context: dict | None = None) -> None:
    ref = (
        _db()
        .collection("users")
        .document(uid)
        .collection("audit_logs")
        .document()
    )
    ref.set(
        {
            "action": action,
            "status": status,
            "message": message,
            "context": context or {},
            "created_at": datetime.now(timezone.utc),
        }
    )


# ────────────────────── Helpers ──────────────────────

def get_all_active_users() -> list[dict[str, Any]]:
    """Retourne tous les utilisateurs actifs (pour le scheduler)."""
    docs = (
        _db()
        .collection("users")
        .where(filter=FieldFilter("is_active", "==", True))
        .stream()
    )
    return [{"uid": d.id, **d.to_dict()} for d in docs]


# ══════════════════════════════════════════════════════
# DCA RSI v2 – Config v2
# ══════════════════════════════════════════════════════

def get_dca_v2_config(uid: str) -> dict[str, Any] | None:
    doc = (
        _db()
        .collection("users")
        .document(uid)
        .collection("dca_config")
        .document("v2")
        .get()
    )
    return doc.to_dict() if doc.exists else None


def update_dca_v2_config(uid: str, data: dict[str, Any]) -> None:
    data["updated_at"] = datetime.now(timezone.utc)
    data["mode"] = "rsi_v2"
    (
        _db()
        .collection("users")
        .document(uid)
        .collection("dca_config")
        .document("v2")
        .set(data, merge=True)
    )
    logger.info("DCA v2 config updated for user %s", uid)


# ══════════════════════════════════════════════════════
# DCA RSI v2 – Spending Tracking
# ══════════════════════════════════════════════════════

def get_spending_record(uid: str, period_key: str) -> dict[str, Any] | None:
    """Récupère un enregistrement de dépenses.
    period_key = 'daily_2026-03-24' | 'weekly_2026-W13' | 'monthly_2026-03'
    """
    doc = (
        _db()
        .collection("users")
        .document(uid)
        .collection("dca_spending")
        .document(period_key)
        .get()
    )
    return doc.to_dict() if doc.exists else None


def increment_spending(uid: str, period_key: str, amount: float) -> None:
    """Incrémente le montant dépensé pour une période (atomique)."""
    from google.cloud.firestore_v1 import transforms

    ref = (
        _db()
        .collection("users")
        .document(uid)
        .collection("dca_spending")
        .document(period_key)
    )
    doc = ref.get()
    if doc.exists:
        ref.update({
            "amount": transforms.Increment(amount),
            "updated_at": datetime.now(timezone.utc),
        })
    else:
        ref.set({
            "period_key": period_key,
            "amount": amount,
            "created_at": datetime.now(timezone.utc),
            "updated_at": datetime.now(timezone.utc),
        })


def get_spending_amounts(uid: str, daily_key: str, weekly_key: str, monthly_key: str) -> dict[str, float]:
    """Retourne les montants dépensés pour les 3 périodes."""
    daily = get_spending_record(uid, daily_key)
    weekly = get_spending_record(uid, weekly_key)
    monthly = get_spending_record(uid, monthly_key)
    return {
        "daily": daily.get("amount", 0.0) if daily else 0.0,
        "weekly": weekly.get("amount", 0.0) if weekly else 0.0,
        "monthly": monthly.get("amount", 0.0) if monthly else 0.0,
    }


# ══════════════════════════════════════════════════════
# DCA RSI v2 – Crash Reserve
# ══════════════════════════════════════════════════════

def get_crash_reserve(uid: str) -> dict[str, Any] | None:
    doc = (
        _db()
        .collection("users")
        .document(uid)
        .collection("crash_reserve")
        .document("main")
        .get()
    )
    return doc.to_dict() if doc.exists else None


def update_crash_reserve(uid: str, data: dict[str, Any]) -> None:
    data["updated_at"] = datetime.now(timezone.utc)
    (
        _db()
        .collection("users")
        .document(uid)
        .collection("crash_reserve")
        .document("main")
        .set(data, merge=True)
    )


def init_crash_reserve(uid: str, total_budget: float) -> None:
    """Initialise la crash reserve pour un utilisateur."""
    ref = (
        _db()
        .collection("users")
        .document(uid)
        .collection("crash_reserve")
        .document("main")
    )
    doc = ref.get()
    if not doc.exists:
        ref.set({
            "total_budget": total_budget,
            "spent": 0.0,
            "remaining": total_budget,
            "levels_triggered": [],
            "last_reset_at": datetime.now(timezone.utc),
            "created_at": datetime.now(timezone.utc),
            "updated_at": datetime.now(timezone.utc),
        })
        logger.info("Crash reserve initialized for user %s: $%.2f", uid, total_budget)


# ══════════════════════════════════════════════════════
# DCA RSI v2 – Boost Cooldown
# ══════════════════════════════════════════════════════

def get_last_boost(uid: str) -> dict[str, Any] | None:
    doc = (
        _db()
        .collection("users")
        .document(uid)
        .collection("dca_boosts")
        .document("last")
        .get()
    )
    return doc.to_dict() if doc.exists else None


def record_boost(uid: str, amount: float) -> None:
    (
        _db()
        .collection("users")
        .document(uid)
        .collection("dca_boosts")
        .document("last")
        .set({
            "amount": amount,
            "triggered_at": datetime.now(timezone.utc),
            "updated_at": datetime.now(timezone.utc),
        })
    )


# ══════════════════════════════════════════════════════
# DCA RSI v2 – Cycle log (détail de chaque exécution)
# ══════════════════════════════════════════════════════

def save_dca_cycle_log(uid: str, data: dict[str, Any]) -> str:
    """Sauve le détail complet d'un cycle DCA (indicateurs, montants, décision)."""
    ref = (
        _db()
        .collection("users")
        .document(uid)
        .collection("dca_cycle_logs")
        .document()
    )
    data["created_at"] = datetime.now(timezone.utc)
    ref.set(data)
    return ref.id


def list_dca_cycle_logs(uid: str, limit: int = 30) -> list[dict[str, Any]]:
    docs = (
        _db()
        .collection("users")
        .document(uid)
        .collection("dca_cycle_logs")
        .order_by("created_at", direction="DESCENDING")
        .limit(limit)
        .stream()
    )
    return [{"log_id": d.id, **d.to_dict()} for d in docs]


# ══════════════════════════════════════════════════════
# Alertes de prix
# ══════════════════════════════════════════════════════

def list_price_alerts(uid: str) -> list[dict[str, Any]]:
    """Liste les alertes de prix d'un utilisateur."""
    docs = (
        _db()
        .collection("users")
        .document(uid)
        .collection("price_alerts")
        .order_by("created_at", direction="DESCENDING")
        .stream()
    )
    result = []
    for d in docs:
        data = d.to_dict()
        data["id"] = d.id
        result.append(data)
    return result


def create_price_alert(
    uid: str, symbol: str, target_price: float, direction: str
) -> dict[str, Any]:
    """Crée une alerte de prix."""
    ref = (
        _db()
        .collection("users")
        .document(uid)
        .collection("price_alerts")
        .document()
    )
    data = {
        "symbol": symbol,
        "target_price": target_price,
        "direction": direction,
        "triggered": False,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    ref.set(data)
    data["id"] = ref.id
    return data


def delete_price_alert(uid: str, alert_id: str) -> None:
    """Supprime une alerte de prix."""
    (
        _db()
        .collection("users")
        .document(uid)
        .collection("price_alerts")
        .document(alert_id)
        .delete()
    )


def get_all_active_alerts() -> list[dict[str, Any]]:
    """Récupère toutes les alertes non déclenchées de tous les utilisateurs."""
    users = get_all_active_users()
    alerts = []
    for user in users:
        uid = user["uid"]
        docs = (
            _db()
            .collection("users")
            .document(uid)
            .collection("price_alerts")
            .where(filter=FieldFilter("triggered", "==", False))
            .stream()
        )
        for d in docs:
            data = d.to_dict()
            data["id"] = d.id
            data["uid"] = uid
            alerts.append(data)
    return alerts


def mark_alert_triggered(uid: str, alert_id: str) -> None:
    """Marque une alerte comme déclenchée."""
    (
        _db()
        .collection("users")
        .document(uid)
        .collection("price_alerts")
        .document(alert_id)
        .update({
            "triggered": True,
            "triggered_at": datetime.now(timezone.utc).isoformat(),
        })
    )


# ══════════════════════════════════════════════════════
# Take-Profit configuration
# ══════════════════════════════════════════════════════

def get_take_profit_config(uid: str) -> dict[str, Any] | None:
    """Récupère la configuration take-profit d'un utilisateur."""
    doc = (
        _db()
        .collection("users")
        .document(uid)
        .collection("take_profit")
        .document("config")
        .get()
    )
    return doc.to_dict() if doc.exists else None


def update_take_profit_config(uid: str, data: dict[str, Any]) -> None:
    """Met à jour la configuration take-profit."""
    data["updated_at"] = datetime.now(timezone.utc)
    (
        _db()
        .collection("users")
        .document(uid)
        .collection("take_profit")
        .document("config")
        .set(data, merge=True)
    )


def get_all_take_profit_configs() -> list[dict[str, Any]]:
    """Récupère les configs take-profit actives de tous les utilisateurs."""
    users = get_all_active_users()
    configs = []
    for user in users:
        uid = user["uid"]
        tp = get_take_profit_config(uid)
        if tp and tp.get("enabled") and tp.get("rules"):
            tp["uid"] = uid
            configs.append(tp)
    return configs
