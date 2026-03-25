"""
Service Market Data – RSI, MA200, MVRV, rolling high.
Calcule les indicateurs nécessaires à la stratégie DCA RSI v2.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

import httpx

from app.core.constants import (
    RSI_PERIOD,
    MA200_PERIOD,
    COINMETRICS_API_URL,
    CRASH_ROLLING_HIGH_DAYS,
    DEFAULT_RSI_BRACKETS,
    DEFAULT_MVRV_THRESHOLDS,
    REGIME_NORMAL,
    REGIME_WEAK,
    REGIME_CAPITULATION,
    CAPITULATION_MA200_FACTOR,
)
from app.logger import get_logger

logger = get_logger(__name__)


# ══════════════════════════════════════════════════════
# RSI (Relative Strength Index)
# ══════════════════════════════════════════════════════

def compute_rsi(closes: list[float], period: int = RSI_PERIOD) -> float:
    """Calcule le RSI à partir d'une liste de prix de clôture (du plus ancien au plus récent).
    Nécessite au moins `period + 1` valeurs.
    """
    if len(closes) < period + 1:
        raise ValueError(f"Need at least {period + 1} closing prices, got {len(closes)}")

    # Calcul des variations
    deltas = [closes[i] - closes[i - 1] for i in range(1, len(closes))]

    # Première moyenne (SMA)
    gains = [d if d > 0 else 0.0 for d in deltas[:period]]
    losses = [-d if d < 0 else 0.0 for d in deltas[:period]]
    avg_gain = sum(gains) / period
    avg_loss = sum(losses) / period

    # Wilder's smoothing pour le reste
    for d in deltas[period:]:
        gain = d if d > 0 else 0.0
        loss = -d if d < 0 else 0.0
        avg_gain = (avg_gain * (period - 1) + gain) / period
        avg_loss = (avg_loss * (period - 1) + loss) / period

    if avg_loss == 0:
        return 100.0

    rs = avg_gain / avg_loss
    rsi = 100.0 - (100.0 / (1.0 + rs))
    return round(rsi, 2)


def get_rsi_bracket(
    rsi: float, brackets: list[dict] | None = None
) -> tuple[str, float]:
    """Retourne (label, multiplier) pour un RSI donné."""
    if brackets is None:
        brackets = DEFAULT_RSI_BRACKETS

    for b in brackets:
        if b["min_rsi"] <= rsi <= b["max_rsi"]:
            return b["label"], b["multiplier"]
        # Gestion des bornes : RSI > 70 → OVERBOUGHT
        if rsi > b.get("max_rsi", 100) and b["label"] == "OVERBOUGHT":
            return b["label"], b["multiplier"]

    # Fallback : bracket le plus strict si RSI hors range
    if rsi >= 70:
        return "OVERBOUGHT", 0
    return "OVERSOLD", 3


# ══════════════════════════════════════════════════════
# MA200 (Moving Average 200 jours)
# ══════════════════════════════════════════════════════

def compute_ma(closes: list[float], period: int = MA200_PERIOD) -> float:
    """Calcule la moyenne mobile simple sur `period` jours."""
    if len(closes) < period:
        raise ValueError(f"Need at least {period} closing prices, got {len(closes)}")
    return sum(closes[-period:]) / period


def get_market_regime(
    price: float, ma200: float
) -> tuple[str, int, int]:
    """Détermine le régime de marché et retourne (regime, btc_pct, eth_pct)."""
    if price < ma200 * CAPITULATION_MA200_FACTOR:
        return REGIME_CAPITULATION, 100, 0
    elif price < ma200:
        return REGIME_WEAK, 95, 5
    else:
        return REGIME_NORMAL, 90, 10


# ══════════════════════════════════════════════════════
# MVRV (Market Value / Realized Value) via CoinMetrics
# ══════════════════════════════════════════════════════

def _build_mvrv_url(asset: str) -> str:
    end_date = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    start_date = (datetime.now(timezone.utc) - timedelta(days=7)).strftime("%Y-%m-%d")
    return (
        f"{COINMETRICS_API_URL}/timeseries/asset-metrics"
        f"?assets={asset}"
        f"&metrics=CapMVRVCur"
        f"&start_time={start_date}"
        f"&end_time={end_date}"
        f"&frequency=1d"
    )


def _parse_mvrv_response(response, asset: str) -> float | None:
    if response.status_code != 200:
        logger.warning("CoinMetrics API error %s: %s", response.status_code, response.text)
        return None
    data = response.json()
    series = data.get("data", [])
    if not series:
        logger.warning("No MVRV data returned from CoinMetrics")
        return None
    latest = series[-1]
    mvrv = float(latest.get("CapMVRVCur", 0))
    logger.info("MVRV ratio for %s: %.4f", asset, mvrv)
    return mvrv


async def fetch_mvrv_ratio(asset: str = "btc") -> float | None:
    """Récupère le MVRV ratio (version async)."""
    try:
        url = _build_mvrv_url(asset)
        async with httpx.AsyncClient() as client:
            response = await client.get(url, timeout=15)
        return _parse_mvrv_response(response, asset)
    except Exception as e:
        logger.error("Failed to fetch MVRV from CoinMetrics: %s", e)
        return None


def fetch_mvrv_ratio_sync(asset: str = "btc") -> float | None:
    """Récupère le MVRV ratio (version sync – safe pour scheduler threads)."""
    try:
        url = _build_mvrv_url(asset)
        response = httpx.get(url, timeout=15)
        return _parse_mvrv_response(response, asset)
    except Exception as e:
        logger.error("Failed to fetch MVRV from CoinMetrics (sync): %s", e)
        return None


def get_mvrv_multiplier(
    mvrv: float | None, thresholds: list[dict] | None = None
) -> float:
    """Retourne le multiplicateur MVRV."""
    if mvrv is None:
        return 1.0  # Pas de boost si donnée indisponible

    if thresholds is None:
        thresholds = DEFAULT_MVRV_THRESHOLDS

    # Trier par max_mvrv croissant pour évaluer dans l'ordre
    sorted_thresholds = sorted(thresholds, key=lambda t: t["max_mvrv"])
    for t in sorted_thresholds:
        if mvrv < t["max_mvrv"]:
            return t["multiplier"]

    return 1.0  # Fallback


# ══════════════════════════════════════════════════════
# Rolling High (pour crash reserve)
# ══════════════════════════════════════════════════════

def compute_rolling_high(
    closes: list[float], days_90: int = 90, days_180: int = 180
) -> float:
    """Calcule le rolling high = max(high 90j, high 180j).
    `closes` doit contenir au moins 180 valeurs (du plus ancien au plus récent).
    """
    if len(closes) < days_180:
        # Utiliser ce qu'on a
        return max(closes) if closes else 0.0

    high_90 = max(closes[-days_90:])
    high_180 = max(closes[-days_180:])
    return max(high_90, high_180)


def compute_drop_pct(current_price: float, rolling_high: float) -> float:
    """Calcule le pourcentage de baisse depuis le rolling high."""
    if rolling_high <= 0:
        return 0.0
    return ((current_price - rolling_high) / rolling_high) * 100


def get_crash_levels_triggered(
    drop_pct: float, levels: list[dict]
) -> list[str]:
    """Retourne les labels des niveaux de crash déclenchés."""
    triggered = []
    for lvl in levels:
        if drop_pct <= lvl["drop_pct"]:
            triggered.append(lvl["label"])
    return triggered


# ══════════════════════════════════════════════════════
# Klines helper (extraction closes depuis Binance klines)
# ══════════════════════════════════════════════════════

def extract_closes_from_klines(klines: list[list]) -> list[float]:
    """Extrait les prix de clôture depuis les klines Binance.
    Format kline : [open_time, open, high, low, close, volume, close_time, ...]
    """
    return [float(k[4]) for k in klines]
