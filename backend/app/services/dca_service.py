"""
Service DCA – logique métier du Dollar Cost Averaging.
Supporte :
  • mode "simple"  – montant fixe quotidien (v1)
  • mode "rsi_v2"  – RSI brackets × MVRV × MA200 regime (v2)
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

import pytz

from app.core.constants import (
    TRADEABLE_STATUSES,
    ORDER_SOURCE_SCHEDULER,
    ORDER_SOURCE_CRASH,
    DEFAULT_RSI_BRACKETS,
    DEFAULT_MVRV_THRESHOLDS,
    DEFAULT_CRASH_LEVELS,
    DCA_V2_VALID_PAIRS,
    DEFAULT_DAILY_CAP,
    DEFAULT_WEEKLY_CAP,
    DEFAULT_MONTHLY_CAP,
    DEFAULT_BOOST_THRESHOLD,
    DEFAULT_BOOST_COOLDOWN_HOURS,
    CRASH_RESET_THRESHOLD_PCT,
    CRASH_ROLLING_HIGH_DAYS,
    DEFAULT_REGIME_RULES,
)
from app.core.exceptions import BinanceError, ExchangeError
from firebase_admin import auth as firebase_auth
from app.services import (
    firestore_service,
    secret_manager_service,
    binance_service,
    revolutx_service,
    portfolio_service,
    telegram_service,
    subscription_service,
    audit_service,
    market_data_service,
    email_service,
)
from app.logger import get_logger

logger = get_logger(__name__)


# ══════════════════════════════════════════════════════
# Helpers exchange-routing
# ══════════════════════════════════════════════════════

def _get_exchange_context(uid: str) -> dict | None:
    """Détermine l'exchange actif et retourne les infos nécessaires.
    Retourne un dict avec exchange, account, creds, ou None si rien n'est connecté.
    """
    exchange = firestore_service.get_active_exchange(uid)

    if exchange == "revolutx":
        account = firestore_service.get_revolutx_account(uid)
        if account and account.get("is_connected"):
            try:
                creds = secret_manager_service.get_revolutx_secret(uid)
                return {"exchange": "revolutx", "account": account, "creds": creds}
            except Exception as e:
                logger.error("Cannot retrieve Revolut X credentials for user %s: %s", uid, e)
                return None

    # Fallback ou exchange == "binance"
    account = firestore_service.get_binance_account(uid)
    if account and account.get("is_connected"):
        try:
            creds = secret_manager_service.get_binance_secret(uid)
            return {"exchange": "binance", "account": account, "creds": creds}
        except Exception as e:
            logger.error("Cannot retrieve Binance credentials for user %s: %s", uid, e)
            return None

    return None


def _place_exchange_order(exchange: str, creds: dict, symbol: str, quote_amount: float) -> dict:
    """Place un ordre market buy sur l'exchange approprié."""
    if exchange == "revolutx":
        return revolutx_service.place_market_buy_order(
            api_key=creds["api_key"],
            private_key_pem=creds["private_key_pem"],
            symbol=symbol,
            quote_amount=quote_amount,
        )
    else:
        return binance_service.place_market_buy_order(
            api_key=creds["api_key"],
            api_secret=creds["api_secret"],
            symbol=symbol,
            quote_amount=quote_amount,
        )


def _get_klines_for_exchange(exchange: str, symbol: str, limit: int = 250) -> list:
    """Récupère les klines quotidiennes selon l'exchange."""
    if exchange == "revolutx":
        return revolutx_service.get_daily_klines_public(symbol, limit)
    else:
        return binance_service.get_daily_klines_public(symbol, limit)


# ══════════════════════════════════════════════════════
# Utilitaires communs
# ══════════════════════════════════════════════════════

def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


def _today_key() -> str:
    return _now_utc().strftime("daily_%Y-%m-%d")


def _week_key() -> str:
    return _now_utc().strftime("weekly_%G-W%V")


def _month_key() -> str:
    return _now_utc().strftime("monthly_%Y-%m")


def should_run_now(config: dict, now: datetime | None = None) -> bool:
    """Vérifie si l'heure actuelle correspond à l'heure d'exécution DCA."""
    tz_name = config.get("timezone", "Europe/Paris")
    tz = pytz.timezone(tz_name)
    if now is None:
        now = datetime.now(tz)
    else:
        now = now.astimezone(tz)

    return (
        now.hour == config.get("execution_hour", -1)
        and now.minute == config.get("execution_minute", -1)
    )


def already_executed_today(uid: str, symbol: str) -> bool:
    """Vérifie si un ordre a déjà été exécuté aujourd'hui pour ce symbole."""
    latest = firestore_service.get_latest_order(uid, symbol)
    if not latest:
        return False

    executed_at = latest.get("executed_at")
    if executed_at is None:
        return False

    if hasattr(executed_at, "date"):
        order_date = executed_at.date()
    else:
        return False

    today = datetime.now(pytz.timezone("Europe/Paris")).date()
    return order_date == today


# Cooldown anti-doublon en secondes (évite 2 ordres si double-clic rapide)
_ORDER_COOLDOWN_SECONDS = 120


def _recently_executed(uid: str, symbol: str) -> bool:
    """Vérifie si un ordre a été exécuté dans les 2 dernières minutes (anti-doublon)."""
    latest = firestore_service.get_latest_order(uid, symbol)
    if not latest:
        return False
    executed_at = latest.get("executed_at")
    if executed_at is None:
        return False
    now = datetime.now(pytz.UTC)
    if hasattr(executed_at, "timestamp"):
        delta = (now - executed_at).total_seconds()
    else:
        return False
    return delta < _ORDER_COOLDOWN_SECONDS


# ══════════════════════════════════════════════════════
# v1 – DCA simple (rétrocompat)
# ══════════════════════════════════════════════════════

def execute_user_dca(uid: str) -> dict | None:
    """Exécute le DCA pour un utilisateur (v1 simple ou dispatch v2)."""
    # 1. Vérifier abonnement
    if not subscription_service.is_active(uid):
        logger.info("Skipping DCA for user %s: subscription not active", uid)
        return None

    # Vérifier si v2
    v2_config = firestore_service.get_dca_v2_config(uid)
    if v2_config and v2_config.get("mode") == "rsi_v2" and v2_config.get("enabled"):
        return _execute_user_dca_v2(uid, v2_config)

    # 2. Vérifier config DCA v1
    config = firestore_service.get_dca_config(uid)
    if not config or not config.get("enabled"):
        logger.info("Skipping DCA for user %s: DCA not enabled", uid)
        return None

    symbol = config["symbol"]
    daily_amount = config["daily_amount_eur"]

    # 3. Vérifier heure d'exécution
    if not should_run_now(config):
        return None

    # 4. Vérifier déjà exécuté aujourd'hui
    force_rebuy = config.get("force_rebuy", False)
    if already_executed_today(uid, symbol):
        if not force_rebuy:
            logger.info("Skipping DCA for user %s: already executed today for %s", uid, symbol)
            _send_skip_telegram(
                uid,
                f"ℹ️ Achat DCA déjà exécuté aujourd'hui pour {symbol}.\n"
                f"Cochez \"Forcer réachat\" dans le dashboard pour bypasser.",
            )
            return None
        # Anti-doublon : même avec force_rebuy, bloquer si ordre < 2 min
        if _recently_executed(uid, symbol):
            logger.info("Skipping DCA for user %s: order too recent (anti-doublon)", uid)
            return None
        logger.info("Force rebuy activated for user %s / %s", uid, symbol)

    # 5. Vérifier exchange connecté
    ctx = _get_exchange_context(uid)
    if not ctx:
        logger.warning("Skipping DCA for user %s: no exchange connected", uid)
        return None

    # 6. Credentials déjà récupérées par _get_exchange_context
    creds = ctx["creds"]
    exchange = ctx["exchange"]

    # 7. Passer l'ordre
    try:
        order_data = _place_exchange_order(exchange, creds, symbol, daily_amount)
    except (BinanceError, ExchangeError) as e:
        logger.error("DCA order failed for user %s: %s", uid, e.message)
        audit_service.log_dca_failed(uid, symbol, e.message)
        err_upper = str(e.message).upper()
        # Message utilisateur clair selon le type d'erreur
        if "NOTIONAL" in err_upper or "MIN_NOTIONAL" in err_upper:
            user_msg = (
                f"⚠️ Montant trop faible pour {symbol}.\n"
                f"Minimum de 5 € par ordre requis.\n"
                f"Montant configuré : {daily_amount:.2f} €.\n\n"
                f"👉 Augmentez votre montant DCA dans le dashboard."
            )
        elif exchange == "revolutx" and (
            "INSUFFICIENT" in err_upper or "BALANCE" in err_upper
            or "FUNDS" in err_upper or "NOT_ENOUGH" in err_upper
        ):
            user_msg = (
                f"⚠️ Solde Revolut X insuffisant pour {symbol}.\n\n"
                f"💰 **Important** : Revolut X utilise un portefeuille \"Cryptos · EUR\" séparé de votre compte EUR principal.\n\n"
                f"👉 **Comment recharger :**\n"
                f"1. Ouvrez l'app Revolut\n"
                f"2. Allez dans **Cryptos** → **Compte Cryptos · EUR**\n"
                f"3. Appuyez sur **Ajouter** ou **Transférer**\n"
                f"4. Transférez des EUR depuis votre compte principal vers Cryptos · EUR\n\n"
                f"💡 Ce transfert est instantané et gratuit."
            )
        elif "INSUFFICIENT" in err_upper or "BALANCE" in err_upper or "FUNDS" in err_upper:
            user_msg = (
                f"⚠️ Solde insuffisant pour {symbol}.\n"
                f"👉 Rechargez votre compte en USDC sur Binance."
            )
        else:
            user_msg = f"Ordre DCA échoué pour {symbol} : {e.message}"
        _send_error_telegram(uid, user_msg)
        return None

    # 8. Enregistrer l'ordre
    order_data["executed_at"] = datetime.now(pytz.UTC)
    order_data["source"] = ORDER_SOURCE_SCHEDULER
    order_id = firestore_service.save_order(uid, order_data)
    order_data["order_id"] = order_id

    # 9. Audit
    audit_service.log_dca_executed(uid, symbol, daily_amount)

    # 9b. Reset force_rebuy si activé
    if force_rebuy:
        firestore_service.update_dca_config(uid, {"force_rebuy": False})
        logger.info("force_rebuy reset to False for user %s", uid)

    # 10. Refresh snapshot
    try:
        portfolio_service.refresh_snapshot(uid, symbol)
    except Exception as e:
        logger.warning("Failed to refresh snapshot for user %s: %s", uid, e)

    # 11. Notification Telegram
    _send_order_telegram(uid, order_data)

    # 12. Notification Email
    _send_order_email(uid, order_data)

    logger.info("DCA executed successfully for user %s / %s", uid, symbol)
    return order_data


# ══════════════════════════════════════════════════════
# v2 – DCA RSI avancé : moteur complet
# ══════════════════════════════════════════════════════

def _execute_user_dca_v2(uid: str, config: dict, *, force_now: bool = False) -> dict | None:
    """Pipeline complet de la stratégie DCA RSI v2.

    1. Heure d'exécution
    2. Vérif Binance / credentials
    3. Récupérer klines (public) → RSI, MA200, rolling high
    4. MVRV (async → sync wrapper)
    5. Calcul montant = base × rsi_mult × mvrv_mult
    6. Régime MA200 → split BTC/ETH
    7. Spending caps
    8. Boost cooldown
    9. Crash reserve
    10. Passage ordres (BTC, ETH)
    11. Enregistrement spending + ordres + audit + cycle log
    12. Notification Telegram
    """
    # ── 1. Heure d'exécution ─────────────────────────
    if not force_now and not should_run_now(config):
        return None

    # ── 2. Exchange connecté + credentials ────────────
    ctx = _get_exchange_context(uid)
    if not ctx:
        logger.warning("DCA v2 skip user %s: no exchange connected", uid)
        return None

    creds = ctx["creds"]
    exchange = ctx["exchange"]

    # Déterminer la quote currency selon l'exchange
    from app.core.constants import EXCHANGE_DEFAULT_QUOTE
    default_quote = EXCHANGE_DEFAULT_QUOTE.get(exchange, "USDC")
    quote = config.get("quote_currency", default_quote)
    pairs = DCA_V2_VALID_PAIRS.get(quote, DCA_V2_VALID_PAIRS["USDC"])
    btc_symbol = pairs["btc"]
    eth_symbol = pairs["eth"]
    base_amount = config.get("base_daily_amount", 12.0)

    # Anti-doublon : si un ordre BTC a été passé il y a < 2 min, skip
    if not force_now and _recently_executed(uid, btc_symbol):
        logger.info("Skipping DCA v2 for user %s: order too recent (anti-doublon)", uid)
        return None

    # ── 3. Klines (API publique) ─────────────────────
    try:
        btc_klines = _get_klines_for_exchange(exchange, btc_symbol, limit=250)
        btc_closes = market_data_service.extract_closes_from_klines(btc_klines)
    except Exception as e:
        logger.error("DCA v2 klines error for %s: %s", uid, e)
        audit_service.log_dca_failed(uid, btc_symbol, f"Klines fetch failed: {e}")
        _send_error_telegram(uid, f"DCA v2 : impossible de récupérer les klines BTC ({e})")
        return None

    btc_price = btc_closes[-1] if btc_closes else 0.0

    # RSI
    try:
        rsi = market_data_service.compute_rsi(btc_closes)
    except ValueError as e:
        logger.error("DCA v2 RSI error: %s", e)
        rsi = 50.0  # Fallback neutral

    rsi_brackets = config.get("rsi_brackets", DEFAULT_RSI_BRACKETS)
    rsi_label, rsi_mult = market_data_service.get_rsi_bracket(rsi, rsi_brackets)

    # MA200
    try:
        ma200 = market_data_service.compute_ma(btc_closes, 200)
    except ValueError:
        ma200 = btc_price  # Pas assez de données → neutral

    regime, btc_pct, eth_pct = market_data_service.get_market_regime(btc_price, ma200)

    # ── 4. MVRV ──────────────────────────────────────
    mvrv_enabled = config.get("mvrv_enabled", True)
    mvrv_value = None
    mvrv_mult = 1.0

    if mvrv_enabled:
        try:
            mvrv_value = market_data_service.fetch_mvrv_ratio_sync("btc")
        except Exception as e:
            logger.warning("DCA v2 MVRV fetch failed: %s", e)

        mvrv_thresholds = config.get("mvrv_thresholds", DEFAULT_MVRV_THRESHOLDS)
        mvrv_mult = market_data_service.get_mvrv_multiplier(mvrv_value, mvrv_thresholds)

    # ── 5. Calcul montant brut ───────────────────────
    raw_amount = base_amount * rsi_mult * mvrv_mult

    # Si RSI = OVERBOUGHT → rsi_mult = 0 → skip
    if raw_amount <= 0:
        logger.info("DCA v2 skip user %s: RSI=%s (OVERBOUGHT), amount=0", uid, rsi)
        audit_service.log_dca_skipped(uid, f"RSI OVERBOUGHT ({rsi:.1f})", {
            "rsi": rsi, "rsi_bracket": rsi_label,
        })
        _save_cycle_log(uid, config, rsi, rsi_label, rsi_mult, mvrv_value, mvrv_mult,
                        btc_price, ma200, regime, btc_pct, eth_pct,
                        0, 0, 0, skipped=True, skip_reason="RSI OVERBOUGHT")
        return None

    # ── 6. Spending caps ─────────────────────────────
    caps = config.get("spending_caps", {})
    daily_cap = caps.get("daily_cap", DEFAULT_DAILY_CAP)
    weekly_cap = caps.get("weekly_cap", DEFAULT_WEEKLY_CAP)
    monthly_cap = caps.get("monthly_cap", DEFAULT_MONTHLY_CAP)

    spending = firestore_service.get_spending_amounts(
        uid, _today_key(), _week_key(), _month_key()
    )

    daily_remaining = max(0.0, daily_cap - spending["daily"])
    weekly_remaining = max(0.0, weekly_cap - spending["weekly"])
    monthly_remaining = max(0.0, monthly_cap - spending["monthly"])
    cap_remaining = min(daily_remaining, weekly_remaining, monthly_remaining)

    capped = False
    cap_reason = None

    if cap_remaining <= 0:
        logger.info("DCA v2 skip user %s: spending cap reached", uid)
        audit_service.log_dca_skipped(uid, "Spending cap reached", {
            "daily_spent": spending["daily"],
            "weekly_spent": spending["weekly"],
            "monthly_spent": spending["monthly"],
        })
        _save_cycle_log(uid, config, rsi, rsi_label, rsi_mult, mvrv_value, mvrv_mult,
                        btc_price, ma200, regime, btc_pct, eth_pct,
                        raw_amount, 0, 0, skipped=True, skip_reason="Spending cap reached")
        return None

    if raw_amount > cap_remaining:
        capped = True
        cap_reason = f"Capped {raw_amount:.2f} → {cap_remaining:.2f}"
        raw_amount = cap_remaining

    # ── 7. Boost cooldown ────────────────────────────
    boost_cfg = config.get("boost", {})
    boost_threshold = boost_cfg.get("threshold", DEFAULT_BOOST_THRESHOLD)
    boost_cooldown_hours = boost_cfg.get("cooldown_hours", DEFAULT_BOOST_COOLDOWN_HOURS)
    boost_cooldown_active = False

    if raw_amount > boost_threshold:
        last_boost = firestore_service.get_last_boost(uid)
        if last_boost:
            triggered_at = last_boost.get("triggered_at")
            if triggered_at:
                # Normaliser timezone
                if hasattr(triggered_at, "timestamp"):
                    if triggered_at.tzinfo is None:
                        triggered_at = triggered_at.replace(tzinfo=timezone.utc)
                    diff = _now_utc() - triggered_at
                    if diff < timedelta(hours=boost_cooldown_hours):
                        boost_cooldown_active = True
                        raw_amount = boost_threshold
                        logger.info(
                            "DCA v2 user %s: boost cooldown active, capping at %.2f",
                            uid, boost_threshold,
                        )

    # ── 8. Split BTC / ETH ──────────────────────────
    btc_amount = round(raw_amount * btc_pct / 100, 2)
    eth_amount = round(raw_amount * eth_pct / 100, 2)
    total_amount = btc_amount + eth_amount

    # Minimum viable order (~1 EUR / 1 USD)
    MIN_ORDER = 1.0
    if btc_amount < MIN_ORDER:
        btc_amount = 0.0
    if eth_amount < MIN_ORDER:
        eth_amount = 0.0

    if btc_amount == 0 and eth_amount == 0:
        logger.info("DCA v2 skip user %s: amounts too small after split", uid)
        audit_service.log_dca_skipped(uid, "Amounts too small", {"raw": raw_amount})
        return None

    # ── 9. Crash reserve check ───────────────────────
    crash_cfg = config.get("crash_reserve", {})
    crash_enabled = crash_cfg.get("enabled", True)
    crash_amount = 0.0
    crash_levels_triggered: list[str] = []

    if crash_enabled and len(btc_closes) >= CRASH_ROLLING_HIGH_DAYS:
        rolling_high = market_data_service.compute_rolling_high(btc_closes)
        drop_pct = market_data_service.compute_drop_pct(btc_price, rolling_high)

        crash_levels = crash_cfg.get("levels", DEFAULT_CRASH_LEVELS)
        # Normaliser en list[dict]
        if crash_levels and not isinstance(crash_levels[0], dict):
            crash_levels = [
                lvl if isinstance(lvl, dict) else lvl.dict()
                for lvl in crash_levels
            ]

        triggered = market_data_service.get_crash_levels_triggered(drop_pct, crash_levels)

        # Charger ou initialiser la reserve
        reserve_state = firestore_service.get_crash_reserve(uid)
        if reserve_state is None:
            total_budget = crash_cfg.get("total_budget", 1100.0)
            firestore_service.init_crash_reserve(uid, total_budget)
            reserve_state = firestore_service.get_crash_reserve(uid) or {
                "total_budget": total_budget,
                "spent": 0.0,
                "remaining": total_budget,
                "levels_triggered": [],
            }

        already_triggered = set(reserve_state.get("levels_triggered", []))

        # Reset logic : si le prix remonte > -10% du rolling high → reset
        if drop_pct > CRASH_RESET_THRESHOLD_PCT and already_triggered:
            logger.info(
                "DCA v2 user %s: crash reserve reset (drop=%.1f%%)", uid, drop_pct
            )
            total_budget = crash_cfg.get("total_budget", 1100.0)
            firestore_service.update_crash_reserve(uid, {
                "total_budget": total_budget,
                "spent": 0.0,
                "remaining": total_budget,
                "levels_triggered": [],
                "last_reset_at": _now_utc(),
            })
            already_triggered = set()

        new_levels = [lvl for lvl in triggered if lvl not in already_triggered]

        if new_levels:
            remaining_budget = reserve_state.get("remaining", 0.0)
            for lvl_name in new_levels:
                lvl_def = next(
                    (lv for lv in crash_levels if lv["label"] == lvl_name), None
                )
                if lvl_def and remaining_budget > 0:
                    pct = lvl_def.get("reserve_pct", 0) / 100
                    level_amount = round(
                        reserve_state.get("total_budget", 1100.0) * pct, 2
                    )
                    level_amount = min(level_amount, remaining_budget)
                    crash_amount += level_amount
                    remaining_budget -= level_amount
                    crash_levels_triggered.append(lvl_name)

    # ── 10. Passage des ordres ───────────────────────
    orders_executed: list[dict] = []
    order_errors: list[str] = []

    # Ordre BTC DCA normal
    if btc_amount > 0:
        btc_order = _place_order_safe(
            uid, creds, btc_symbol, btc_amount, ORDER_SOURCE_SCHEDULER, exchange,
            errors_out=order_errors,
        )
        if btc_order:
            orders_executed.append(btc_order)

    # Ordre ETH DCA normal
    if eth_amount > 0:
        eth_order = _place_order_safe(
            uid, creds, eth_symbol, eth_amount, ORDER_SOURCE_SCHEDULER, exchange,
            errors_out=order_errors,
        )
        if eth_order:
            orders_executed.append(eth_order)

    # Ordres crash reserve (tout en BTC)
    if crash_amount > 0:
        crash_order = _place_order_safe(
            uid, creds, btc_symbol, crash_amount, ORDER_SOURCE_CRASH, exchange,
            errors_out=order_errors,
        )
        if crash_order:
            orders_executed.append(crash_order)
            # Mettre à jour la reserve
            reserve_state = firestore_service.get_crash_reserve(uid) or {}
            new_spent = reserve_state.get("spent", 0.0) + crash_amount
            all_triggered = list(
                set(reserve_state.get("levels_triggered", []))
                | set(crash_levels_triggered)
            )
            firestore_service.update_crash_reserve(uid, {
                "spent": new_spent,
                "remaining": max(
                    0, reserve_state.get("total_budget", 1100.0) - new_spent
                ),
                "levels_triggered": all_triggered,
            })
            for lvl in crash_levels_triggered:
                audit_service.log_crash_buy(uid, btc_symbol, crash_amount, lvl)

    if not orders_executed:
        logger.warning("DCA v2 user %s: no orders executed", uid)
        if order_errors:
            return {"_no_orders": True, "errors": order_errors}
        return None

    # ── 11. Enregistrement spending ──────────────────
    actual_spent = btc_amount + eth_amount  # Crash reserve hors caps
    if actual_spent > 0:
        firestore_service.increment_spending(uid, _today_key(), actual_spent)
        firestore_service.increment_spending(uid, _week_key(), actual_spent)
        firestore_service.increment_spending(uid, _month_key(), actual_spent)

    # Boost record
    if actual_spent > boost_threshold and not boost_cooldown_active:
        firestore_service.record_boost(uid, actual_spent)

    # ── 12. Audit + Cycle Log ────────────────────────
    audit_service.log_dca_v2_executed(
        uid=uid,
        total_amount=actual_spent + crash_amount,
        btc_amount=btc_amount + crash_amount,
        eth_amount=eth_amount,
        rsi=rsi,
        regime=regime,
    )

    _save_cycle_log(
        uid, config, rsi, rsi_label, rsi_mult, mvrv_value, mvrv_mult,
        btc_price, ma200, regime, btc_pct, eth_pct,
        btc_amount, eth_amount, crash_amount,
        capped=capped, cap_reason=cap_reason,
        boost_cooldown=boost_cooldown_active,
        crash_levels=crash_levels_triggered,
    )

    # ── 13. Notification Telegram ────────────────────
    _send_v2_telegram(
        uid, rsi, rsi_label, regime, btc_amount, eth_amount,
        crash_amount, crash_levels_triggered, orders_executed,
    )

    # ── 14. Notification Email ────────────────────────
    _send_v2_email(
        uid, rsi, rsi_label, regime, btc_amount, eth_amount,
        crash_amount, crash_levels_triggered, orders_executed,
    )

    # Refresh snapshots
    for sym in {btc_symbol, eth_symbol}:
        try:
            portfolio_service.refresh_snapshot(uid, sym)
        except Exception as e:
            logger.warning("Failed to refresh snapshot for %s/%s: %s", uid, sym, e)

    logger.info(
        "DCA v2 executed for %s: RSI=%.1f (%s) regime=%s BTC=%.2f ETH=%.2f crash=%.2f",
        uid, rsi, rsi_label, regime, btc_amount, eth_amount, crash_amount,
    )

    return orders_executed[0] if orders_executed else None


# ══════════════════════════════════════════════════════
# Helpers internes v2
# ══════════════════════════════════════════════════════

def _place_order_safe(
    uid: str, creds: dict, symbol: str, amount: float, source: str,
    exchange: str = "binance", *, errors_out: list[str] | None = None,
) -> dict | None:
    """Place un ordre et enregistre. Retourne None en cas d'échec."""
    try:
        order_data = _place_exchange_order(exchange, creds, symbol, amount)
        order_data["executed_at"] = _now_utc()
        order_data["source"] = source
        order_id = firestore_service.save_order(uid, order_data)
        order_data["order_id"] = order_id
        return order_data
    except (BinanceError, ExchangeError) as e:
        logger.error("DCA v2 order failed for %s on %s: %s", uid, symbol, e.message)
        audit_service.log_dca_failed(uid, symbol, e.message)
        if errors_out is not None:
            errors_out.append(f"{symbol}: {e.message}")
        err_upper = str(e.message).upper()
        if "NOTIONAL" in err_upper:
            user_msg = (
                f"⚠️ Montant trop faible pour {symbol}.\n"
                f"Minimum de 5 € par ordre requis.\n\n"
                f"👉 Augmentez votre montant DCA de base dans le dashboard."
            )
        elif exchange == "revolutx" and (
            "INSUFFICIENT" in err_upper or "BALANCE" in err_upper
            or "FUNDS" in err_upper or "NOT_ENOUGH" in err_upper
        ):
            user_msg = (
                f"⚠️ Solde Revolut X insuffisant pour {symbol}.\n\n"
                f"💰 **Important** : Revolut X utilise un portefeuille \"Cryptos · EUR\" séparé de votre compte EUR principal.\n\n"
                f"👉 **Comment recharger :**\n"
                f"1. Ouvrez l'app Revolut\n"
                f"2. Allez dans **Cryptos** → **Compte Cryptos · EUR**\n"
                f"3. Appuyez sur **Ajouter** ou **Transférer**\n"
                f"4. Transférez des EUR depuis votre compte principal vers Cryptos · EUR\n\n"
                f"💡 Ce transfert est instantané et gratuit."
            )
        elif "INSUFFICIENT" in err_upper or "BALANCE" in err_upper or "FUNDS" in err_upper:
            user_msg = (
                f"⚠️ Solde insuffisant pour {symbol}.\n"
                f"👉 Rechargez votre compte en USDC sur Binance."
            )
        else:
            user_msg = f"Ordre DCA v2 échoué ({symbol}): {e.message}"
        _send_error_telegram(uid, user_msg)
        return None


def _save_cycle_log(
    uid: str, config: dict,
    rsi: float, rsi_label: str, rsi_mult: float,
    mvrv: float | None, mvrv_mult: float,
    btc_price: float, ma200: float,
    regime: str, btc_pct: int, eth_pct: int,
    btc_amount: float, eth_amount: float, crash_amount: float,
    skipped: bool = False, skip_reason: str | None = None,
    capped: bool = False, cap_reason: str | None = None,
    boost_cooldown: bool = False,
    crash_levels: list[str] | None = None,
) -> None:
    """Enregistre un log détaillé du cycle v2."""
    try:
        firestore_service.save_dca_cycle_log(uid, {
            "mode": "rsi_v2",
            "rsi": rsi,
            "rsi_bracket": rsi_label,
            "rsi_multiplier": rsi_mult,
            "mvrv": mvrv,
            "mvrv_multiplier": mvrv_mult,
            "btc_price": btc_price,
            "ma200": ma200,
            "regime": regime,
            "btc_pct": btc_pct,
            "eth_pct": eth_pct,
            "btc_amount": btc_amount,
            "eth_amount": eth_amount,
            "crash_amount": crash_amount,
            "total_amount": btc_amount + eth_amount + crash_amount,
            "base_daily_amount": config.get("base_daily_amount", 0),
            "skipped": skipped,
            "skip_reason": skip_reason,
            "capped": capped,
            "cap_reason": cap_reason,
            "boost_cooldown_active": boost_cooldown,
            "crash_levels_triggered": crash_levels or [],
        })
    except Exception as e:
        logger.warning("Failed to save cycle log for %s: %s", uid, e)


def _send_v2_telegram(
    uid: str,
    rsi: float, rsi_label: str, regime: str,
    btc_amount: float, eth_amount: float,
    crash_amount: float, crash_levels: list[str],
    orders: list[dict],
) -> None:
    """Envoie une notification Telegram riche pour le DCA v2."""
    telegram_settings = firestore_service.get_telegram_settings(uid)
    if not telegram_settings:
        return
    if not telegram_settings.get("enabled") or not telegram_settings.get("notify_orders"):
        return
    chat_id = telegram_settings.get("chat_id")
    if not chat_id:
        return

    # Déterminer le symbole monétaire
    cs = "€" if any(o.get("symbol", "").endswith("-EUR") for o in orders) else "$"

    total = btc_amount + eth_amount + crash_amount
    lines = [
        "📊 <b>DCA RSI v2 exécuté</b>",
        f"RSI : <code>{rsi:.1f}</code> ({rsi_label})",
        f"Régime : <code>{regime}</code>",
        f"BTC : <code>{btc_amount:.2f} {cs}</code> | ETH : <code>{eth_amount:.2f} {cs}</code>",
    ]
    if crash_amount > 0:
        lines.append(
            f"🚨 Crash reserve : <code>{crash_amount:.2f} {cs}</code> ({', '.join(crash_levels)})"
        )
    lines.append(f"<b>Total : {total:.2f} {cs}</b>")

    # Détails par ordre
    for o in orders:
        sym = o.get('symbol', '?')
        qty = o.get('quantity', 0)
        price = o.get('price', 0)
        est = " (estimé)" if o.get('estimated') else ""
        lines.append(f"  • {sym} : {qty:.8f} @ {price:,.2f} {cs}{est}")

    message = "\n".join(lines)

    try:
        telegram_service.send_message_sync(chat_id, message)
    except Exception as e:
        logger.warning("Failed to send DCA v2 Telegram notification: %s", e)


# ══════════════════════════════════════════════════════
# Calcul preview (sans exécuter d'ordre)
# ══════════════════════════════════════════════════════

def compute_v2_preview(uid: str) -> dict[str, Any]:
    """Calcule ce que ferait le DCA v2 maintenant, sans passer d'ordre.
    Utilisé par l'endpoint GET /dca/v2/status.
    """
    config = firestore_service.get_dca_v2_config(uid)
    if not config:
        return {"error": "No v2 config found"}

    # Déterminer l'exchange actif pour les klines
    exchange = firestore_service.get_active_exchange(uid)
    from app.core.constants import EXCHANGE_DEFAULT_QUOTE
    default_quote = EXCHANGE_DEFAULT_QUOTE.get(exchange, "USDC")
    quote = config.get("quote_currency", default_quote)
    pairs = DCA_V2_VALID_PAIRS.get(quote, DCA_V2_VALID_PAIRS["USDC"])
    btc_symbol = pairs["btc"]
    base_amount = config.get("base_daily_amount", 12.0)

    # Klines
    try:
        klines = _get_klines_for_exchange(exchange, btc_symbol, limit=250)
        closes = market_data_service.extract_closes_from_klines(klines)
    except Exception as e:
        return {"error": f"Klines unavailable: {e}"}

    btc_price = closes[-1] if closes else 0.0

    # RSI
    try:
        rsi = market_data_service.compute_rsi(closes)
    except ValueError:
        rsi = 50.0
    rsi_label, rsi_mult = market_data_service.get_rsi_bracket(
        rsi, config.get("rsi_brackets", DEFAULT_RSI_BRACKETS)
    )

    # MA200
    try:
        ma200 = market_data_service.compute_ma(closes, 200)
    except ValueError:
        ma200 = btc_price
    regime, btc_pct, eth_pct = market_data_service.get_market_regime(btc_price, ma200)

    # MVRV
    mvrv_value = None
    mvrv_mult = 1.0
    if config.get("mvrv_enabled", True):
        try:
            mvrv_value = market_data_service.fetch_mvrv_ratio_sync("btc")
        except Exception:
            pass
        mvrv_mult = market_data_service.get_mvrv_multiplier(
            mvrv_value, config.get("mvrv_thresholds", DEFAULT_MVRV_THRESHOLDS)
        )

    raw_amount = base_amount * rsi_mult * mvrv_mult
    btc_amount = round(raw_amount * btc_pct / 100, 2)
    eth_amount = round(raw_amount * eth_pct / 100, 2)

    # Spending
    spending = firestore_service.get_spending_amounts(
        uid, _today_key(), _week_key(), _month_key()
    )
    caps = config.get("spending_caps", {})

    # Crash
    crash_info: dict[str, Any] = {}
    if (
        config.get("crash_reserve", {}).get("enabled", True)
        and len(closes) >= CRASH_ROLLING_HIGH_DAYS
    ):
        rolling_high = market_data_service.compute_rolling_high(closes)
        drop_pct = market_data_service.compute_drop_pct(btc_price, rolling_high)
        crash_levels = config.get("crash_reserve", {}).get("levels", DEFAULT_CRASH_LEVELS)
        triggered = market_data_service.get_crash_levels_triggered(drop_pct, crash_levels)
        reserve = firestore_service.get_crash_reserve(uid)
        crash_info = {
            "rolling_high": rolling_high,
            "drop_pct": round(drop_pct, 2),
            "triggered_levels": triggered,
            "reserve_remaining": reserve.get("remaining", 0) if reserve else 0,
        }

    return {
        "btc_price": btc_price,
        "rsi": rsi,
        "rsi_bracket": rsi_label,
        "rsi_multiplier": rsi_mult,
        "mvrv": mvrv_value,
        "mvrv_multiplier": mvrv_mult,
        "ma200": round(ma200, 2),
        "regime": regime,
        "btc_pct": btc_pct,
        "eth_pct": eth_pct,
        "base_amount": base_amount,
        "raw_amount": round(raw_amount, 2),
        "btc_amount": btc_amount,
        "eth_amount": eth_amount,
        "spending": spending,
        "caps": {
            "daily_cap": caps.get("daily_cap", DEFAULT_DAILY_CAP),
            "weekly_cap": caps.get("weekly_cap", DEFAULT_WEEKLY_CAP),
            "monthly_cap": caps.get("monthly_cap", DEFAULT_MONTHLY_CAP),
        },
        "crash_reserve": crash_info,
    }


# ══════════════════════════════════════════════════════
# Telegram helpers (v1 compat)
# ══════════════════════════════════════════════════════

def _send_order_telegram(uid: str, order: dict) -> None:
    """Envoie la notification Telegram d'ordre (fire-and-forget)."""
    telegram_settings = firestore_service.get_telegram_settings(uid)
    if not telegram_settings:
        return
    if not telegram_settings.get("enabled") or not telegram_settings.get("notify_orders"):
        return
    chat_id = telegram_settings.get("chat_id")
    if not chat_id:
        return
    try:
        telegram_service.send_order_notification_sync(chat_id, order)
    except Exception as e:
        logger.warning("Failed to send Telegram order notification: %s", e)


def _send_skip_telegram(uid: str, message: str) -> None:
    """Envoie un message Telegram quand le DCA est skip (fire-and-forget, une seule fois par jour)."""
    telegram_settings = firestore_service.get_telegram_settings(uid)
    if not telegram_settings:
        return
    if not telegram_settings.get("enabled"):
        return
    chat_id = telegram_settings.get("chat_id")
    if not chat_id:
        return

    # Vérifier si on a déjà envoyé ce message aujourd'hui
    config = firestore_service.get_dca_config(uid)
    today_str = datetime.now(pytz.timezone("Europe/Paris")).strftime("%Y-%m-%d")
    if config and config.get("_skip_notified_date") == today_str:
        return  # Déjà notifié aujourd'hui, pas de spam
    firestore_service.update_dca_config(uid, {"_skip_notified_date": today_str})

    try:
        telegram_service.send_message_sync(chat_id, message)
    except Exception as e:
        logger.warning("Failed to send Telegram skip notification: %s", e)


def _send_error_telegram(uid: str, error_message: str) -> None:
    """Envoie la notification Telegram d'erreur (fire-and-forget)."""
    telegram_settings = firestore_service.get_telegram_settings(uid)
    if not telegram_settings:
        return
    if not telegram_settings.get("enabled") or not telegram_settings.get("notify_errors"):
        return
    chat_id = telegram_settings.get("chat_id")
    if not chat_id:
        return
    try:
        telegram_service.send_error_notification_sync(chat_id, error_message)
    except Exception as e:
        logger.warning("Failed to send Telegram error notification: %s", e)


def _get_user_email(uid: str) -> str | None:
    """Récupère l'email de l'utilisateur depuis Firebase Auth."""
    try:
        firebase_user = firebase_auth.get_user(uid)
        return firebase_user.email or None
    except Exception:
        return None


def _send_order_email(uid: str, order: dict) -> None:
    """Envoie un email de confirmation d'achat DCA (fire-and-forget)."""
    email = _get_user_email(uid)
    if not email:
        return
    try:
        email_service.send_order_email(email, order)
    except Exception as e:
        logger.warning("Failed to send order email to %s: %s", email, e)


def _send_v2_email(
    uid: str,
    rsi: float, rsi_label: str, regime: str,
    btc_amount: float, eth_amount: float,
    crash_amount: float, crash_levels: list[str],
    orders: list[dict],
) -> None:
    """Envoie un email récapitulatif DCA v2 (fire-and-forget)."""
    email = _get_user_email(uid)
    if not email:
        return
    try:
        email_service.send_v2_order_email(
            email, rsi, rsi_label, regime,
            btc_amount, eth_amount,
            crash_amount, crash_levels, orders,
        )
    except Exception as e:
        logger.warning("Failed to send v2 email to %s: %s", email, e)


# ══════════════════════════════════════════════════════
# Simulation de scénarios (grille RSI × MVRV × Regime)
# ══════════════════════════════════════════════════════

def simulate_scenarios(
    base_daily_amount: float,
    rsi_brackets: list[dict] | None = None,
    mvrv_thresholds: list[dict] | None = None,
    regime_rules: list[dict] | None = None,
    spending_caps: dict | None = None,
) -> dict[str, Any]:
    """Génère la grille complète de tous les scénarios RSI × MVRV × Regime.

    Retourne un dict avec :
      - scenarios : list[dict] (chaque combinaison)
      - extremes : {min_daily, max_daily, avg_monthly_low, avg_monthly_high}
      - auto_params : paramètres auto-calculés
    """
    from app.schemas.dca import compute_auto_params

    brackets = rsi_brackets or DEFAULT_RSI_BRACKETS
    thresholds = mvrv_thresholds or DEFAULT_MVRV_THRESHOLDS
    regimes = regime_rules or DEFAULT_REGIME_RULES

    auto = compute_auto_params(base_daily_amount)
    caps = spending_caps or auto["spending_caps"]
    daily_cap = caps.get("daily_cap", 9999)

    scenarios: list[dict] = []
    all_amounts: list[float] = []

    for bracket in brackets:
        rsi_label = bracket["label"]
        rsi_mult = bracket["multiplier"]

        for threshold in thresholds:
            mvrv_label = threshold["label"]
            mvrv_mult = threshold["multiplier"]

            raw = base_daily_amount * rsi_mult * mvrv_mult

            # Appliquer le cap quotidien
            capped = raw > daily_cap
            effective = min(raw, daily_cap) if raw > 0 else 0

            # Pour chaque régime
            for regime in regimes:
                regime_label = regime["label"]
                btc_pct = regime["btc_pct"]
                eth_pct = regime["eth_pct"]

                btc_amount = round(effective * btc_pct / 100, 2)
                eth_amount = round(effective * eth_pct / 100, 2)

                note = ""
                if rsi_mult == 0:
                    note = "⏸️ Pas d'achat (RSI overbought)"
                elif mvrv_mult >= 2.0:
                    note = "🔥 Accumulation forte"
                elif mvrv_mult >= 1.5:
                    note = "📈 Accumulation modérée"

                if capped and effective > 0:
                    note += f" ⚠️ Cappé à {daily_cap:.0f}"

                row = {
                    "rsi_bracket": rsi_label,
                    "rsi_multiplier": rsi_mult,
                    "mvrv_label": mvrv_label,
                    "mvrv_multiplier": mvrv_mult,
                    "regime": regime_label,
                    "raw_amount": round(raw, 2),
                    "btc_amount": btc_amount,
                    "eth_amount": eth_amount,
                    "total_amount": round(btc_amount + eth_amount, 2),
                    "capped": capped and effective > 0,
                    "note": note.strip(),
                }
                scenarios.append(row)
                if effective > 0:
                    all_amounts.append(effective)

    # Calcul des extrêmes
    extremes = {}
    if all_amounts:
        extremes = {
            "min_daily": min(all_amounts),
            "max_daily": max(all_amounts),
            "avg_daily": round(sum(all_amounts) / len(all_amounts), 2),
            "est_monthly_min": round(min(all_amounts) * 30, 2),
            "est_monthly_max": round(max(all_amounts) * 30, 2),
            "est_monthly_avg": round((sum(all_amounts) / len(all_amounts)) * 30, 2),
        }

    return {
        "base_daily_amount": base_daily_amount,
        "auto_params": auto,
        "scenarios": scenarios,
        "extremes": extremes,
    }


# ══════════════════════════════════════════════════════
# Cycle runner (appelé par le scheduler)
# ══════════════════════════════════════════════════════

def run_cycle() -> int:
    """Exécute un cycle DCA complet pour tous les utilisateurs actifs.
    Retourne le nombre d'ordres exécutés.
    """
    users = firestore_service.get_all_active_users()
    executed = 0

    for user in users:
        uid = user["uid"]
        try:
            result = execute_user_dca(uid)
            if result:
                executed += 1
        except Exception as e:
            logger.error("Error in DCA cycle for user %s: %s", uid, e)

    logger.info("DCA cycle complete: %d orders executed", executed)
    return executed
