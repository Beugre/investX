"""
Schémas Pydantic – Portfolio & Ordres.
"""

from __future__ import annotations

from datetime import datetime
from pydantic import BaseModel


class OrderRead(BaseModel):
    order_id: str | None = None
    symbol: str
    side: str = "BUY"
    amount_eur: float
    quantity: float
    price: float
    status: str
    exchange_order_id: str | None = None
    executed_at: datetime | None = None
    source: str = "scheduler"
    error_message: str | None = None


class PortfolioSnapshot(BaseModel):
    symbol: str
    quantity_total: float = 0.0
    invested_total_eur: float = 0.0
    avg_buy_price: float = 0.0
    market_price: float = 0.0
    market_value_eur: float = 0.0
    pnl_value_eur: float = 0.0
    pnl_percent: float = 0.0
    total_commission: float = 0.0
    commission_asset: str = ""
    captured_at: datetime | None = None


class PortfolioSummary(BaseModel):
    snapshots: list[PortfolioSnapshot] = []


class BinanceConnectRequest(BaseModel):
    api_key: str
    api_secret: str


class BinanceStatusResponse(BaseModel):
    is_connected: bool = False
    exchange: str = "binance"
    label: str | None = None
    permissions_validated: bool = False


class RevolutXConnectRequest(BaseModel):
    api_key: str
    private_key_pem: str


class RevolutXStatusResponse(BaseModel):
    is_connected: bool = False
    exchange: str = "revolutx"
    label: str | None = None
    permissions_validated: bool = False
