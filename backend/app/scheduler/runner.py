"""
Scheduler DCA – APScheduler pour exécution périodique.
"""

from __future__ import annotations

from apscheduler.schedulers.background import BackgroundScheduler

from app.services.dca_service import run_cycle
from app.logger import get_logger

logger = get_logger(__name__)

scheduler = BackgroundScheduler()


def start_scheduler() -> None:
    """Démarre le scheduler DCA (exécution toutes les minutes)."""
    scheduler.add_job(
        run_cycle,
        trigger="interval",
        minutes=1,
        id="dca_cycle",
        replace_existing=True,
        max_instances=1,
    )
    scheduler.start()
    logger.info("DCA scheduler started (interval: 1 minute)")


def stop_scheduler() -> None:
    """Arrête le scheduler."""
    if scheduler.running:
        scheduler.shutdown(wait=False)
        logger.info("DCA scheduler stopped")
