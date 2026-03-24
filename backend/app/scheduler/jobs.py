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
    """Rafraîchit les snapshots portfolio (prix, PnL) pour tous les utilisateurs actifs."""
    try:
        users = firestore_service.get_all_active_users()
        refreshed = 0
        for user in users:
            uid = user["uid"]
            config = firestore_service.get_dca_config(uid)
            if not config or not config.get("enabled"):
                continue
            symbol = config.get("symbol", "BTCUSDC")
            try:
                portfolio_service.refresh_snapshot(uid, symbol)
                refreshed += 1
            except Exception as e:
                logger.warning("Portfolio refresh failed for %s: %s", uid, e)
        if refreshed:
            logger.info("Portfolio refresh completed: %d snapshots updated", refreshed)
    except Exception as e:
        logger.error("Portfolio refresh job failed: %s", e)
