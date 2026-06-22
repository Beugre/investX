"""
Endpoints DCA config :
  v1 : /dca/config, /dca/enable, /dca/disable
  v2 : /dca/v2/config, /dca/v2/status, /dca/v2/spending, /dca/v2/crash-reserve
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from app.core.auth_firebase import get_current_uid
from app.schemas.dca import (
    DCAConfigRead,
    DCAConfigUpdate,
    DCAV2ConfigRead,
    DCAV2ConfigUpdate,
    DCASpendingStatus,
    CrashReserveStatus,
    SimulationRequest,
    SimulationResponse,
    AutoConfigResponse,
    compute_auto_params,
    SpendingCaps,
    BoostConfig,
)
from app.services import firestore_service, dca_service, subscription_service

router = APIRouter(prefix="/dca", tags=["DCA"])


@router.get("/config", response_model=DCAConfigRead)
async def get_dca_config(uid: str = Depends(get_current_uid)):
    """Retourne la configuration DCA de l'utilisateur."""
    config = firestore_service.get_dca_config(uid)
    if not config:
        return DCAConfigRead()
    return DCAConfigRead(**config)


@router.put("/config", response_model=DCAConfigRead)
async def update_dca_config(
    payload: DCAConfigUpdate,
    uid: str = Depends(get_current_uid),
):
    """Met à jour la configuration DCA."""
    from app.core.constants import ALLOWED_SYMBOLS
    data = payload.model_dump()
    if data.get("symbol") and data["symbol"] not in ALLOWED_SYMBOLS:
        from app.core.exceptions import BadRequest
        raise BadRequest(f"Symbol '{data['symbol']}' not allowed")
    firestore_service.update_dca_config(uid, data)
    return DCAConfigRead(**data)


@router.post("/enable")
async def enable_dca(uid: str = Depends(get_current_uid)):
    """Active le DCA."""
    firestore_service.update_dca_config(uid, {"enabled": True})
    return {"message": "DCA enabled"}


@router.post("/disable")
async def disable_dca(uid: str = Depends(get_current_uid)):
    """Désactive le DCA."""
    firestore_service.update_dca_config(uid, {"enabled": False})
    return {"message": "DCA disabled"}


# ══════════════════════════════════════════════════════
# v2 – DCA RSI avancé
# ══════════════════════════════════════════════════════

@router.get("/v2/config", response_model=DCAV2ConfigRead)
async def get_dca_v2_config(uid: str = Depends(get_current_uid)):
    """Retourne la configuration DCA RSI v2."""
    config = firestore_service.get_dca_v2_config(uid)
    if not config:
        return DCAV2ConfigRead()
    return DCAV2ConfigRead(**config)


@router.put("/v2/config", response_model=DCAV2ConfigRead)
async def update_dca_v2_config(
    payload: DCAV2ConfigUpdate,
    uid: str = Depends(get_current_uid),
):
    """Met à jour la configuration DCA RSI v2."""
    data = payload.model_dump(exclude_none=True)
    firestore_service.update_dca_v2_config(uid, data)
    # Relire pour retourner la config complète (avec les valeurs par défaut)
    updated = firestore_service.get_dca_v2_config(uid)
    return DCAV2ConfigRead(**(updated or data))


@router.post("/v2/enable")
async def enable_dca_v2(uid: str = Depends(get_current_uid)):
    """Active le DCA RSI v2 (et désactive le v1)."""
    firestore_service.update_dca_v2_config(uid, {"enabled": True})
    # Désactiver le v1 pour éviter les conflits
    firestore_service.update_dca_config(uid, {"enabled": False})
    return {"message": "DCA RSI v2 enabled"}


@router.post("/v2/disable")
async def disable_dca_v2(uid: str = Depends(get_current_uid)):
    """Désactive le DCA RSI v2."""
    firestore_service.update_dca_v2_config(uid, {"enabled": False})
    return {"message": "DCA RSI v2 disabled"}


@router.post("/v2/force-execute")
async def force_execute_dca_v2(uid: str = Depends(get_current_uid)):
    """Force l'exécution immédiate du DCA v2 (ignore l'heure programmée)."""
    config = firestore_service.get_dca_v2_config(uid)
    if not config or not config.get("enabled"):
        return {"message": "DCA v2 not enabled", "executed": False}
    result = dca_service._execute_user_dca_v2(uid, config, force_now=True)
    if result and isinstance(result, dict) and result.get("_no_orders"):
        errors = result.get("errors", [])
        msg = "Ordres échoués : " + " | ".join(errors) if errors else "Aucun ordre passé"
        return {"message": msg, "executed": False, "errors": errors}
    if result:
        return {"message": "DCA v2 executed", "executed": True, "orders": result if isinstance(result, list) else [result]}
    return {"message": "Aucun ordre : RSI overbought ou caps atteints", "executed": False}


@router.get("/v2/status")
async def get_dca_v2_status(uid: str = Depends(get_current_uid)):
    """Aperçu en temps réel : indicateurs + montant calculé (sans exécuter).
    Utile pour le dashboard et le debug.
    """
    return dca_service.compute_v2_preview(uid)


@router.get("/v2/spending", response_model=DCASpendingStatus)
async def get_dca_v2_spending(uid: str = Depends(get_current_uid)):
    """Retourne l'état des dépenses DCA (daily/weekly/monthly)."""
    from app.core.constants import DEFAULT_DAILY_CAP, DEFAULT_WEEKLY_CAP, DEFAULT_MONTHLY_CAP

    config = firestore_service.get_dca_v2_config(uid)
    caps = (config or {}).get("spending_caps", {})
    daily_cap = caps.get("daily_cap", DEFAULT_DAILY_CAP)
    weekly_cap = caps.get("weekly_cap", DEFAULT_WEEKLY_CAP)
    monthly_cap = caps.get("monthly_cap", DEFAULT_MONTHLY_CAP)

    spending = firestore_service.get_spending_amounts(
        uid,
        dca_service._today_key(),
        dca_service._week_key(),
        dca_service._month_key(),
    )

    return DCASpendingStatus(
        spent_today=spending["daily"],
        spent_this_week=spending["weekly"],
        spent_this_month=spending["monthly"],
        daily_cap=daily_cap,
        weekly_cap=weekly_cap,
        monthly_cap=monthly_cap,
        daily_remaining=max(0, daily_cap - spending["daily"]),
        weekly_remaining=max(0, weekly_cap - spending["weekly"]),
        monthly_remaining=max(0, monthly_cap - spending["monthly"]),
    )


@router.get("/v2/crash-reserve", response_model=CrashReserveStatus)
async def get_dca_v2_crash_reserve(uid: str = Depends(get_current_uid)):
    """Retourne l'état de la crash reserve."""
    from app.core.constants import DEFAULT_CRASH_RESERVE_BUDGET

    reserve = firestore_service.get_crash_reserve(uid)
    if not reserve:
        return CrashReserveStatus()

    return CrashReserveStatus(
        total_budget=reserve.get("total_budget", DEFAULT_CRASH_RESERVE_BUDGET),
        spent=reserve.get("spent", 0.0),
        remaining=reserve.get("remaining", DEFAULT_CRASH_RESERVE_BUDGET),
        levels_triggered=reserve.get("levels_triggered", []),
        last_reset_at=reserve.get("last_reset_at"),
    )


@router.get("/v2/cycle-logs")
async def get_dca_v2_cycle_logs(
    limit: int = 30,
    uid: str = Depends(get_current_uid),
):
    """Retourne les N derniers cycle logs DCA v2."""
    return firestore_service.list_dca_cycle_logs(uid, limit=limit)


# ══════════════════════════════════════════════════════
# Auto-calcul + Simulation
# ══════════════════════════════════════════════════════

@router.get("/v2/auto-config")
async def get_auto_config(
    base_daily_amount: float = 12.0,
):
    """Calcule les paramètres recommandés à partir du montant de base.
    Pas besoin d'auth : utile aussi pour la page de démo.
    """
    auto = compute_auto_params(base_daily_amount)
    caps = auto["spending_caps"]
    boost = auto["boost"]

    return AutoConfigResponse(
        base_daily_amount=base_daily_amount,
        spending_caps=SpendingCaps(**caps),
        boost=BoostConfig(**boost),
        crash_reserve_budget=auto["crash_reserve"]["total_budget"],
    )


@router.post("/v2/simulate", response_model=SimulationResponse)
async def simulate_dca_v2(payload: SimulationRequest):
    """Génère la grille complète RSI × MVRV × Regime pour un montant de base.
    Pas besoin d'auth : permet à l'utilisateur de tester avant de configurer.
    """
    result = dca_service.simulate_scenarios(
        base_daily_amount=payload.base_daily_amount,
        rsi_brackets=[b.model_dump() for b in payload.rsi_brackets] if payload.rsi_brackets else None,
        mvrv_thresholds=[t.model_dump() for t in payload.mvrv_thresholds] if payload.mvrv_thresholds else None,
        regime_rules=[r.model_dump() for r in payload.regime_rules] if payload.regime_rules else None,
        spending_caps=payload.spending_caps.model_dump() if payload.spending_caps else None,
    )
    return SimulationResponse(**result)


# ══════════════════════════════════════════════════════
# Take-Profit (DCA exit)
# ══════════════════════════════════════════════════════

from pydantic import BaseModel, Field


class TakeProfitRule(BaseModel):
    symbol: str = Field(..., examples=["BTCUSDC"])
    target_price: float = Field(..., gt=0)
    sell_pct: float = Field(50.0, ge=1, le=100, description="% du holding à vendre")


class TakeProfitConfigUpdate(BaseModel):
    enabled: bool = False
    rules: list[TakeProfitRule] = []


@router.get("/v2/take-profit")
async def get_take_profit_config(uid: str = Depends(get_current_uid)):
    """Retourne la configuration take-profit."""
    tp = firestore_service.get_take_profit_config(uid)
    return tp or {"enabled": False, "rules": []}


@router.put("/v2/take-profit")
async def update_take_profit_config(
    payload: TakeProfitConfigUpdate,
    uid: str = Depends(get_current_uid),
):
    """Met à jour la configuration take-profit."""
    from app.core.constants import ALLOWED_SYMBOLS
    from app.core.exceptions import BadRequest
    for rule in payload.rules:
        if rule.symbol not in ALLOWED_SYMBOLS:
            raise BadRequest(f"Symbol '{rule.symbol}' not allowed")
    data = payload.model_dump()
    firestore_service.update_take_profit_config(uid, data)
    return data


# ══════════════════════════════════════════════════════
# Backtesting
# ══════════════════════════════════════════════════════

@router.get("/v2/backtest")
async def backtest_dca_v2(
    base_daily_amount: float = Query(12.0, gt=0),
    days: int = Query(365, ge=30, le=1095),
    symbol: str = Query("BTCUSDC"),
):
    """Backtesting de la stratégie RSI v2 sur données historiques.
    Endpoint public (pas besoin d'auth).
    """
    from app.core.constants import ALLOWED_SYMBOLS
    from app.core.exceptions import BadRequest
    if symbol not in ALLOWED_SYMBOLS:
        raise BadRequest(f"Symbol '{symbol}' not allowed")
    return dca_service.backtest_rsi_v2(base_daily_amount, days, symbol)
