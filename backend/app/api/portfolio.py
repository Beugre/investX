"""
Endpoints Portfolio : /portfolio/summary, /portfolio/history, /orders, /orders/export
"""

from __future__ import annotations

import csv
import io
from typing import Optional, List

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse

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

    symbol = config.get("symbol", "BTCUSDC")

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
    symbol: str = Query("BTCUSDC"),
):
    """Retourne le dernier ordre pour un symbole."""
    order = firestore_service.get_latest_order(uid, symbol)
    if not order:
        return None
    return OrderRead(**order)


@router.get("/orders/export")
async def export_orders_csv(
    uid: str = Depends(get_current_uid),
    symbol: str | None = Query(None),
    limit: int = Query(500, ge=1, le=5000),
):
    """Exporte les ordres en CSV."""
    orders = firestore_service.list_orders(uid, limit=limit, symbol=symbol)
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "date", "symbol", "side", "quantity", "price",
        "amount_eur", "commission", "order_type", "exchange",
    ])
    for o in orders:
        writer.writerow([
            o.get("created_at", ""),
            o.get("symbol", ""),
            o.get("side", "BUY"),
            o.get("quantity", 0),
            o.get("price", 0),
            o.get("amount_eur", 0),
            o.get("commission", o.get("fees_usd", 0)),
            o.get("order_type", "market"),
            o.get("exchange", ""),
        ])
    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=investx_orders.csv"},
    )
