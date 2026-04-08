"""
Jobs planifiés – wrapper pour le scheduler.
"""

from app.services.dca_service import run_cycle
from app.services import firestore_service, portfolio_service
from app.logger import get_logger

logger = get_logger(__name__)


def dca_job() -> None:
    """Job de cycle DCA, appelé par le scheduler."""
    try:
        executed = run_cycle()
        logger.info("DCA job completed: %d orders executed", executed)
    except Exception as e:
        logger.error("DCA job failed: %s", e)


def portfolio_refresh_job() -> None:
    """Rafraîchit les snapshots portfolio (prix, PnL) pour tous les utilisateurs actifs.
    Supporte à la fois le DCA v1 (une paire) et le DCA v2 (multi-paires).
    """
    try:
        users = firestore_service.get_all_active_users()
        refreshed = 0
        for user in users:
            uid = user["uid"]
            symbols_to_refresh: set[str] = set()

            # v2 multi-paires
            v2_config = firestore_service.get_dca_v2_config(uid)
            if v2_config and v2_config.get("enabled"):
                pairs = v2_config.get("pairs") or []
                for p in pairs:
                    sym = p.get("symbol") if isinstance(p, dict) else None
                    if sym:
                        symbols_to_refresh.add(sym)
                # Fallback BTC/ETH si pas de paires custom
                if not symbols_to_refresh:
                    quote = v2_config.get("quote_currency", "USDC")
                    from app.core.constants import DCA_V2_VALID_PAIRS
                    vp = DCA_V2_VALID_PAIRS.get(quote, DCA_V2_VALID_PAIRS["USDC"])
                    symbols_to_refresh.update(vp.values())
            else:
                # v1
                config = firestore_service.get_dca_config(uid)
                if config and config.get("enabled"):
                    symbols_to_refresh.add(config.get("symbol", "BTCUSDC"))

            for symbol in symbols_to_refresh:
                try:
                    portfolio_service.refresh_snapshot(uid, symbol)
                    refreshed += 1
                except Exception as e:
                    logger.warning("Portfolio refresh failed for %s/%s: %s", uid, symbol, e)
        if refreshed:
            logger.info("Portfolio refresh completed: %d snapshots updated", refreshed)
    except Exception as e:
        logger.error("Portfolio refresh job failed: %s", e)
