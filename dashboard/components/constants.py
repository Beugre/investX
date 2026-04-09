"""
Constantes centralisées pour le dashboard.
Évite la duplication des listes de paires dans chaque page.
"""

# ── Paires Binance (USDC) ──
BINANCE_PAIRS = ["BTCUSDC", "ETHUSDC", "SOLUSDC"]
BINANCE_ALL_PAIRS = ["BTCUSDC", "ETHUSDC", "BNBUSDC", "ADAUSDC", "SOLUSDC"]

# ── Paires Revolut X ──
REVOLUTX_PAIRS = ["BTC-EUR", "ETH-EUR", "SOL-EUR", "BTC-USDC", "ETH-USDC", "SOL-USDC"]
REVOLUTX_ALL_PAIRS = [
    "BTC-EUR", "ETH-EUR", "BNB-EUR", "ADA-EUR", "SOL-EUR",
    "BTC-USDC", "ETH-USDC", "SOL-USDC",
]

# ── Toutes les paires pour les alertes ──
ALERT_SYMBOLS = [
    "BTCUSDC", "ETHUSDC", "SOLUSDC", "BNBUSDC", "ADAUSDC",
    "BTC-EUR", "ETH-EUR", "SOL-EUR", "BNB-EUR", "ADA-EUR",
    "BTC-USDC", "ETH-USDC", "SOL-USDC",
]

# ── Timezones courantes ──
COMMON_TIMEZONES = [
    "Europe/Paris",
    "Europe/London",
    "Europe/Berlin",
    "Europe/Zurich",
    "Europe/Brussels",
    "America/New_York",
    "America/Chicago",
    "America/Los_Angeles",
    "Asia/Tokyo",
    "Asia/Singapore",
    "UTC",
]
