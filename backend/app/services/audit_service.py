"""
Service Audit – journalisation minimale des actions.
"""

from __future__ import annotations

from app.services import firestore_service
from app.core.constants import (
    AUDIT_DCA_EXECUTED,
    AUDIT_DCA_FAILED,
    AUDIT_DCA_SKIPPED,
    AUDIT_CRASH_BUY,
    AUDIT_BINANCE_CONNECTED,
    AUDIT_BINANCE_DISCONNECTED,
    AUDIT_REVOLUTX_CONNECTED,
    AUDIT_REVOLUTX_DISCONNECTED,
    AUDIT_SUBSCRIPTION_UPDATED,
    AUDIT_TELEGRAM_LINKED,
)


def log_dca_executed(uid: str, symbol: str, amount_eur: float) -> None:
    firestore_service.save_audit_log(
        uid=uid,
        action=AUDIT_DCA_EXECUTED,
        status="SUCCESS",
        message="Daily DCA order executed",
        context={"symbol": symbol, "amount_eur": amount_eur},
    )


def log_dca_failed(uid: str, symbol: str, error: str) -> None:
    firestore_service.save_audit_log(
        uid=uid,
        action=AUDIT_DCA_FAILED,
        status="ERROR",
        message=f"DCA order failed: {error}",
        context={"symbol": symbol},
    )


def log_binance_connected(uid: str) -> None:
    firestore_service.save_audit_log(
        uid=uid,
        action=AUDIT_BINANCE_CONNECTED,
        status="SUCCESS",
        message="Binance account connected",
    )


def log_binance_disconnected(uid: str) -> None:
    firestore_service.save_audit_log(
        uid=uid,
        action=AUDIT_BINANCE_DISCONNECTED,
        status="SUCCESS",
        message="Binance account disconnected",
    )


def log_revolutx_connected(uid: str) -> None:
    firestore_service.save_audit_log(
        uid=uid,
        action=AUDIT_REVOLUTX_CONNECTED,
        status="SUCCESS",
        message="Revolut X account connected",
    )


def log_revolutx_disconnected(uid: str) -> None:
    firestore_service.save_audit_log(
        uid=uid,
        action=AUDIT_REVOLUTX_DISCONNECTED,
        status="SUCCESS",
        message="Revolut X account disconnected",
    )


def log_subscription_updated(uid: str, status: str) -> None:
    firestore_service.save_audit_log(
        uid=uid,
        action=AUDIT_SUBSCRIPTION_UPDATED,
        status="INFO",
        message=f"Subscription status: {status}",
        context={"subscription_status": status},
    )


def log_telegram_linked(uid: str, chat_id: str) -> None:
    firestore_service.save_audit_log(
        uid=uid,
        action=AUDIT_TELEGRAM_LINKED,
        status="SUCCESS",
        message="Telegram linked",
        context={"chat_id": chat_id},
    )


# ── DCA RSI v2 audit helpers ──

def log_dca_skipped(uid: str, reason: str, context: dict | None = None) -> None:
    firestore_service.save_audit_log(
        uid=uid,
        action=AUDIT_DCA_SKIPPED,
        status="INFO",
        message=f"DCA skipped: {reason}",
        context=context or {},
    )


def log_crash_buy(uid: str, symbol: str, amount: float, level: str) -> None:
    firestore_service.save_audit_log(
        uid=uid,
        action=AUDIT_CRASH_BUY,
        status="SUCCESS",
        message=f"Crash reserve buy: {level}",
        context={"symbol": symbol, "amount": amount, "level": level},
    )


def log_dca_v2_executed(
    uid: str, total_amount: float, btc_amount: float, eth_amount: float,
    rsi: float, regime: str,
) -> None:
    firestore_service.save_audit_log(
        uid=uid,
        action=AUDIT_DCA_EXECUTED,
        status="SUCCESS",
        message="DCA RSI v2 executed",
        context={
            "total_amount": total_amount,
            "btc_amount": btc_amount,
            "eth_amount": eth_amount,
            "rsi": rsi,
            "regime": regime,
        },
    )
