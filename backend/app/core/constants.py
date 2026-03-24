"""
Constantes centralisées de l'application.
"""

from typing import Final

# ── Paires autorisées ──
ALLOWED_SYMBOLS: Final[list[str]] = [
    "BTCEUR",
    "ETHEUR",
    "BTCUSDT",
    "ETHUSDT",
    "BNBEUR",
    "ADAEUR",
    "SOLEUR",
]

# ── Paires DCA RSI v2 ──
DCA_V2_BTC_SYMBOLS: Final[list[str]] = ["BTCEUR", "BTCUSDT"]
DCA_V2_ETH_SYMBOLS: Final[list[str]] = ["ETHEUR", "ETHUSDT"]
DCA_V2_VALID_PAIRS: Final[dict[str, dict[str, str]]] = {
    "EUR": {"btc": "BTCEUR", "eth": "ETHEUR"},
    "USD": {"btc": "BTCUSDT", "eth": "ETHUSDT"},
}

# ── Timezone par défaut ──
DEFAULT_TIMEZONE: Final[str] = "Europe/Paris"

# ── Statuts d'abonnement Stripe ──
SUBSCRIPTION_ACTIVE: Final[str] = "active"
SUBSCRIPTION_PAST_DUE: Final[str] = "past_due"
SUBSCRIPTION_CANCELED: Final[str] = "canceled"
SUBSCRIPTION_INCOMPLETE: Final[str] = "incomplete"

TRADEABLE_STATUSES: Final[set[str]] = {SUBSCRIPTION_ACTIVE}

# ── Sources d'ordre ──
ORDER_SOURCE_SCHEDULER: Final[str] = "scheduler"
ORDER_SOURCE_MANUAL: Final[str] = "manual"
ORDER_SOURCE_CRASH: Final[str] = "crash_reserve"

# ══════════════════════════════════════════════════════
# ── DCA RSI v2 : Brackets RSI ──
# ══════════════════════════════════════════════════════

RSI_PERIOD: Final[int] = 14  # RSI classique 14 jours

# RSI brackets : (label, min_rsi_exclusive, max_rsi_inclusive, multiplier)
RSI_BRACKET_OVERBOUGHT: Final[str] = "OVERBOUGHT"
RSI_BRACKET_WARM: Final[str] = "WARM"
RSI_BRACKET_NEUTRAL: Final[str] = "NEUTRAL"
RSI_BRACKET_OVERSOLD: Final[str] = "OVERSOLD"

DEFAULT_RSI_BRACKETS: Final[list[dict]] = [
    {"label": RSI_BRACKET_OVERBOUGHT, "min_rsi": 70, "max_rsi": 100, "multiplier": 0},
    {"label": RSI_BRACKET_WARM,       "min_rsi": 55, "max_rsi": 70,  "multiplier": 1},
    {"label": RSI_BRACKET_NEUTRAL,    "min_rsi": 45, "max_rsi": 55,  "multiplier": 2},
    {"label": RSI_BRACKET_OVERSOLD,   "min_rsi": 0,  "max_rsi": 45,  "multiplier": 3},
]

# ── DCA RSI v2 : MVRV thresholds ──
DEFAULT_MVRV_THRESHOLDS: Final[list[dict]] = [
    {"label": "DEEP_UNDERVALUED", "max_mvrv": 0.85, "multiplier": 2.0},
    {"label": "MODERATE_UNDERVALUED", "max_mvrv": 1.0, "multiplier": 1.5},
    {"label": "FAIR_OR_ABOVE", "max_mvrv": 999.0, "multiplier": 1.0},
]

# ── DCA RSI v2 : Régime de marché (MA200) ──
MA200_PERIOD: Final[int] = 200

REGIME_NORMAL: Final[str] = "NORMAL"
REGIME_WEAK: Final[str] = "WEAK"
REGIME_CAPITULATION: Final[str] = "CAPITULATION"

DEFAULT_REGIME_RULES: Final[list[dict]] = [
    # Ordre d'évaluation : du plus extrême au plus normal
    {"label": REGIME_CAPITULATION, "condition": "price < ma200 * 0.85", "btc_pct": 100, "eth_pct": 0},
    {"label": REGIME_WEAK,         "condition": "price < ma200",        "btc_pct": 95,  "eth_pct": 5},
    {"label": REGIME_NORMAL,       "condition": "price >= ma200",       "btc_pct": 90,  "eth_pct": 10},
]

CAPITULATION_MA200_FACTOR: Final[float] = 0.85

# ── DCA RSI v2 : Spending Caps (défauts) ──
DEFAULT_DAILY_CAP: Final[float] = 150.0
DEFAULT_WEEKLY_CAP: Final[float] = 400.0
DEFAULT_MONTHLY_CAP: Final[float] = 1500.0

# ── DCA RSI v2 : Boost Cooldown ──
DEFAULT_BOOST_THRESHOLD: Final[float] = 120.0  # Au-delà, cooldown
DEFAULT_BOOST_COOLDOWN_HOURS: Final[int] = 24

# ── DCA RSI v2 : Crash Reserve ──
DEFAULT_CRASH_RESERVE_BUDGET: Final[float] = 1100.0

# ── DCA RSI v2 : Auto-calc multipliers (par rapport à base_daily_amount) ──
# Ces ratios servent à dériver automatiquement chaque paramètre
# quand l'utilisateur ne renseigne que le montant de base quotidien.
AUTO_DAILY_CAP_RATIO: Final[float] = 12.5      # daily_cap  = base × 12.5
AUTO_WEEKLY_CAP_RATIO: Final[float] = 33.3      # weekly_cap = base × 33.3
AUTO_MONTHLY_CAP_RATIO: Final[float] = 125.0    # monthly_cap = base × 125
AUTO_BOOST_THRESHOLD_RATIO: Final[float] = 10.0 # boost_threshold = base × 10
AUTO_CRASH_BUDGET_RATIO: Final[float] = 91.7    # crash_budget = base × 91.7
CRASH_ROLLING_HIGH_DAYS: Final[int] = 180  # max(90j, 180j)
CRASH_RESET_THRESHOLD_PCT: Final[float] = -10.0  # Reset quand > -10% du rolling high

DEFAULT_CRASH_LEVELS: Final[list[dict]] = [
    {"label": "LEVEL_15", "drop_pct": -15.0, "reserve_pct": 25},
    {"label": "LEVEL_25", "drop_pct": -25.0, "reserve_pct": 35},
    {"label": "LEVEL_35", "drop_pct": -35.0, "reserve_pct": 40},
]

# ── CoinMetrics API ──
COINMETRICS_API_URL: Final[str] = "https://community-api.coinmetrics.io/v4"

# ── Actions d'audit ──
AUDIT_DCA_EXECUTED: Final[str] = "DCA_ORDER_EXECUTED"
AUDIT_DCA_FAILED: Final[str] = "DCA_ORDER_FAILED"
AUDIT_DCA_SKIPPED: Final[str] = "DCA_ORDER_SKIPPED"
AUDIT_CRASH_BUY: Final[str] = "CRASH_RESERVE_BUY"
AUDIT_BINANCE_CONNECTED: Final[str] = "BINANCE_CONNECTED"
AUDIT_BINANCE_DISCONNECTED: Final[str] = "BINANCE_DISCONNECTED"
AUDIT_SUBSCRIPTION_UPDATED: Final[str] = "SUBSCRIPTION_UPDATED"
AUDIT_TELEGRAM_LINKED: Final[str] = "TELEGRAM_LINKED"
