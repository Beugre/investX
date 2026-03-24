"""
Schémas Pydantic – Configuration DCA (v1 simple + v2 RSI).
"""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, field_validator

from app.core.constants import (
    ALLOWED_SYMBOLS,
    DEFAULT_RSI_BRACKETS,
    DEFAULT_MVRV_THRESHOLDS,
    DEFAULT_REGIME_RULES,
    DEFAULT_DAILY_CAP,
    DEFAULT_WEEKLY_CAP,
    DEFAULT_MONTHLY_CAP,
    DEFAULT_BOOST_THRESHOLD,
    DEFAULT_BOOST_COOLDOWN_HOURS,
    DEFAULT_CRASH_RESERVE_BUDGET,
    DEFAULT_CRASH_LEVELS,
    AUTO_DAILY_CAP_RATIO,
    AUTO_WEEKLY_CAP_RATIO,
    AUTO_MONTHLY_CAP_RATIO,
    AUTO_BOOST_THRESHOLD_RATIO,
    AUTO_CRASH_BUDGET_RATIO,
)


# ══════════════════════════════════════════════════════
# v1 – DCA simple (rétrocompat)
# ══════════════════════════════════════════════════════

class DCAConfigRead(BaseModel):
    enabled: bool = False
    symbol: str = "BTCEUR"
    daily_amount_eur: float = 1.0
    execution_hour: int = 10
    execution_minute: int = 0
    timezone: str = "Europe/Paris"
    mode: str = "simple"


class DCAConfigUpdate(BaseModel):
    enabled: bool
    symbol: str
    daily_amount_eur: float = Field(gt=0)
    execution_hour: int = Field(ge=0, le=23)
    execution_minute: int = Field(ge=0, le=59)
    timezone: str = "Europe/Paris"
    mode: Literal["simple", "rsi_v2"] = "simple"

    @field_validator("symbol")
    @classmethod
    def validate_symbol(cls, v: str) -> str:
        if v not in ALLOWED_SYMBOLS:
            raise ValueError(f"Symbol must be one of {ALLOWED_SYMBOLS}")
        return v


# ══════════════════════════════════════════════════════
# v2 – DCA RSI avancé
# ══════════════════════════════════════════════════════

class RSIBracket(BaseModel):
    label: str
    min_rsi: float = Field(ge=0, le=100)
    max_rsi: float = Field(ge=0, le=100)
    multiplier: float = Field(ge=0)


class MVRVThreshold(BaseModel):
    label: str
    max_mvrv: float
    multiplier: float = Field(gt=0)


class RegimeRule(BaseModel):
    label: str
    condition: str
    btc_pct: int = Field(ge=0, le=100)
    eth_pct: int = Field(ge=0, le=100)


class CrashLevel(BaseModel):
    label: str
    drop_pct: float = Field(lt=0)
    reserve_pct: int = Field(ge=0, le=100)


class SpendingCaps(BaseModel):
    daily_cap: float = Field(default=DEFAULT_DAILY_CAP, gt=0)
    weekly_cap: float = Field(default=DEFAULT_WEEKLY_CAP, gt=0)
    monthly_cap: float = Field(default=DEFAULT_MONTHLY_CAP, gt=0)


class BoostConfig(BaseModel):
    threshold: float = Field(default=DEFAULT_BOOST_THRESHOLD, gt=0)
    cooldown_hours: int = Field(default=DEFAULT_BOOST_COOLDOWN_HOURS, ge=0)


class CrashReserveConfig(BaseModel):
    enabled: bool = True
    total_budget: float = Field(default=DEFAULT_CRASH_RESERVE_BUDGET, ge=0)
    levels: list[CrashLevel] = Field(
        default_factory=lambda: [CrashLevel(**lvl) for lvl in DEFAULT_CRASH_LEVELS]
    )


class DCAV2ConfigRead(BaseModel):
    """Configuration complète DCA RSI v2 en lecture."""
    enabled: bool = False
    mode: str = "rsi_v2"

    # Paire de base (quote currency)
    quote_currency: str = "EUR"  # EUR ou USD

    # Montants
    base_daily_amount: float = 12.0  # montant de base (×1)

    # Exécution
    execution_hour: int = 10  # heure UTC
    execution_minute: int = 0
    timezone: str = "UTC"

    # RSI brackets
    rsi_brackets: list[RSIBracket] = Field(
        default_factory=lambda: [RSIBracket(**b) for b in DEFAULT_RSI_BRACKETS]
    )

    # MVRV multiplier
    mvrv_enabled: bool = True
    mvrv_thresholds: list[MVRVThreshold] = Field(
        default_factory=lambda: [MVRVThreshold(**t) for t in DEFAULT_MVRV_THRESHOLDS]
    )

    # Régime de marché (MA200)
    regime_rules: list[RegimeRule] = Field(
        default_factory=lambda: [RegimeRule(**r) for r in DEFAULT_REGIME_RULES]
    )

    # Spending caps
    spending_caps: SpendingCaps = Field(default_factory=SpendingCaps)

    # Boost cooldown
    boost: BoostConfig = Field(default_factory=BoostConfig)

    # Crash reserve
    crash_reserve: CrashReserveConfig = Field(default_factory=CrashReserveConfig)


class DCAV2ConfigUpdate(BaseModel):
    """Payload de mise à jour DCA RSI v2."""
    enabled: bool
    quote_currency: Literal["EUR", "USD"] = "EUR"
    base_daily_amount: float = Field(gt=0)
    execution_hour: int = Field(ge=0, le=23)
    execution_minute: int = Field(ge=0, le=59)
    timezone: str = "UTC"

    rsi_brackets: list[RSIBracket] | None = None
    mvrv_enabled: bool = True
    mvrv_thresholds: list[MVRVThreshold] | None = None
    regime_rules: list[RegimeRule] | None = None
    spending_caps: SpendingCaps | None = None
    boost: BoostConfig | None = None
    crash_reserve: CrashReserveConfig | None = None


# ══════════════════════════════════════════════════════
# Résultat du calcul DCA (pour logs / notifications)
# ══════════════════════════════════════════════════════

class DCACalculationResult(BaseModel):
    """Résultat du calcul de montant DCA RSI v2."""
    # Inputs
    rsi_value: float
    rsi_bracket: str
    rsi_multiplier: float
    mvrv_value: float | None = None
    mvrv_multiplier: float = 1.0
    btc_price: float = 0.0
    ma200: float = 0.0
    regime: str = "NORMAL"

    # Répartition
    btc_pct: int = 90
    eth_pct: int = 10

    # Montants calculés
    base_amount: float = 0.0
    amount_after_rsi: float = 0.0
    amount_after_mvrv: float = 0.0
    final_btc_amount: float = 0.0
    final_eth_amount: float = 0.0
    total_amount: float = 0.0

    # Caps
    capped: bool = False
    cap_reason: str | None = None

    # Crash reserve
    crash_triggered: bool = False
    crash_levels_triggered: list[str] = Field(default_factory=list)
    crash_amount: float = 0.0

    # Boost
    boost_applied: bool = False
    boost_cooldown_active: bool = False

    # Skip
    skipped: bool = False
    skip_reason: str | None = None


class DCASpendingStatus(BaseModel):
    """Suivi des dépenses DCA."""
    spent_today: float = 0.0
    spent_this_week: float = 0.0
    spent_this_month: float = 0.0
    daily_cap: float = DEFAULT_DAILY_CAP
    weekly_cap: float = DEFAULT_WEEKLY_CAP
    monthly_cap: float = DEFAULT_MONTHLY_CAP
    daily_remaining: float = DEFAULT_DAILY_CAP
    weekly_remaining: float = DEFAULT_WEEKLY_CAP
    monthly_remaining: float = DEFAULT_MONTHLY_CAP


class CrashReserveStatus(BaseModel):
    """Statut de la crash reserve."""
    total_budget: float = DEFAULT_CRASH_RESERVE_BUDGET
    spent: float = 0.0
    remaining: float = DEFAULT_CRASH_RESERVE_BUDGET
    rolling_high: float = 0.0
    current_drop_pct: float = 0.0
    levels_triggered: list[str] = Field(default_factory=list)
    last_reset_at: datetime | None = None


# ══════════════════════════════════════════════════════
# Auto-calcul des paramètres à partir du montant de base
# ══════════════════════════════════════════════════════

def compute_auto_params(base_daily_amount: float) -> dict:
    """Dérive tous les paramètres configurables à partir du montant de base.

    L'utilisateur peut ensuite overrider chaque valeur manuellement.
    La logique :
      - daily_cap   = base × 12.5  (couvre OVERSOLD×3 × DEEP_MVRV×2 + marge)
      - weekly_cap  = base × 33.3  (≈ daily_cap × 2.67, pas tous les jours au max)
      - monthly_cap = base × 125   (≈ weekly × 3.75)
      - boost_threshold = base × 10 (seuil au-delà duquel on applique le cooldown)
      - crash_reserve_budget = base × 91.7 (≈ 3 mois de base)
    """
    b = base_daily_amount
    return {
        "spending_caps": {
            "daily_cap": round(b * AUTO_DAILY_CAP_RATIO, 2),
            "weekly_cap": round(b * AUTO_WEEKLY_CAP_RATIO, 2),
            "monthly_cap": round(b * AUTO_MONTHLY_CAP_RATIO, 2),
        },
        "boost": {
            "threshold": round(b * AUTO_BOOST_THRESHOLD_RATIO, 2),
            "cooldown_hours": DEFAULT_BOOST_COOLDOWN_HOURS,
        },
        "crash_reserve": {
            "enabled": True,
            "total_budget": round(b * AUTO_CRASH_BUDGET_RATIO, 2),
        },
    }


class AutoConfigResponse(BaseModel):
    """Réponse de l'endpoint auto-config : valeurs dérivées du montant de base."""
    base_daily_amount: float
    spending_caps: SpendingCaps
    boost: BoostConfig
    crash_reserve_budget: float
    scenarios: list[dict] = Field(default_factory=list)


# ══════════════════════════════════════════════════════
# Scénarios de simulation
# ══════════════════════════════════════════════════════

class ScenarioRow(BaseModel):
    """Une ligne de la grille de simulation RSI × MVRV."""
    rsi_bracket: str
    rsi_multiplier: float
    mvrv_label: str
    mvrv_multiplier: float
    regime: str
    raw_amount: float
    btc_amount: float
    eth_amount: float
    total_amount: float
    capped: bool = False
    note: str = ""


class SimulationRequest(BaseModel):
    """Paramètres de simulation envoyés par le front."""
    base_daily_amount: float = Field(gt=0)
    rsi_brackets: list[RSIBracket] | None = None
    mvrv_thresholds: list[MVRVThreshold] | None = None
    regime_rules: list[RegimeRule] | None = None
    spending_caps: SpendingCaps | None = None


class SimulationResponse(BaseModel):
    """Grille complète RSI × MVRV avec les montants résultants."""
    base_daily_amount: float
    auto_params: dict = Field(default_factory=dict)
    scenarios: list[ScenarioRow] = Field(default_factory=list)
    extremes: dict = Field(default_factory=dict)
