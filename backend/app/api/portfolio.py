"""
Endpoints Portfolio : /portfolio/summary, /portfolio/history, /orders
"""

from __future__ import annotations

from typing import Optional, List

from fastapi import APIRouter, Depends, Query

from app.core.auth_firebase import get_current_uid
from app.schemas.portfolio import PortfolioSummary, PortfolioSnapshot, OrderRead
from app.services import firestore_service, portfolio_service

router = APIRouter(tags=["Portfolio"])


@router.get("/portfolio/summary", response_model=PortfolioSummary)
async def get_portfolio_summary(uid: str = Depends(get_current_uid)):
    """Retourne le résumé portfolio (snapshots les plus récents)."""
    config = firestore_service.get_dca_config(uid)
    if not config:
        return PortfolioSummary()

    symbol = config.get("symbol", "BTCEUR")

    # Essayer d'utiliser le dernier snapshot en base
    snap = firestore_service.get_latest_snapshot(uid, symbol)
    if snap:
        snapshots = [PortfolioSnapshot(**snap)]
    else:
        snapshots = []

    return PortfolioSummary(snapshots=snapshots)


@router.get("/portfolio/history", response_model=list[PortfolioSnapshot])
async def get_portfolio_history(
    uid: str = Depends(get_current_uid),
    symbol: str | None = Query(None),
    limit: int = Query(30, ge=1, le=365),
):
    """Retourne l'historique des snapshots portfolio."""
    snaps = firestore_service.list_snapshots(uid, symbol=symbol, limit=limit)
    return [PortfolioSnapshot(**s) for s in snaps]


@router.get("/orders", response_model=list[OrderRead])
async def list_orders(
    uid: str = Depends(get_current_uid),
    symbol: str | None = Query(None),
    limit: int = Query(50, ge=1, le=500),
):
    """Retourne les ordres de l'utilisateur."""
    orders = firestore_service.list_orders(uid, limit=limit, symbol=symbol)
    return [OrderRead(**o) for o in orders]


@router.get("/orders/latest", response_model=Optional[OrderRead])
async def get_latest_order(
    uid: str = Depends(get_current_uid),
    symbol: str = Query("BTCEUR"),
):
    """Retourne le dernier ordre pour un symbole."""
    order = firestore_service.get_latest_order(uid, symbol)
    if not order:
        return None
    return OrderRead(**order)
