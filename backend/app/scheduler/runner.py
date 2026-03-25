"""
Scheduler DCA – APScheduler pour exécution périodique.
"""

from __future__ import annotations

from apscheduler.schedulers.background import BackgroundScheduler

from app.services.dca_service import run_cycle
from app.scheduler.jobs import portfolio_refresh_job
from app.scheduler.health_job import health_check_job
from app.logger import get_logger

logger = get_logger(__name__)

scheduler = BackgroundScheduler()


def start_scheduler() -> None:
    """Démarre le scheduler DCA + refresh portfolio (toutes les minutes)."""
    scheduler.add_job(
        run_cycle,
        trigger="interval",
        minutes=1,
        id="dca_cycle",
        replace_existing=True,
        max_instances=1,
    )
    scheduler.add_job(
        portfolio_refresh_job,
        trigger="interval",
        minutes=1,
        id="portfolio_refresh",
        replace_existing=True,
        max_instances=1,
    )
    scheduler.add_job(
        health_check_job,
        trigger="interval",
        minutes=5,
        id="health_check",
        replace_existing=True,
        max_instances=1,
    )
    scheduler.start()
    logger.info("Scheduler started (DCA cycle + portfolio refresh + health check)")


def stop_scheduler() -> None:
    """Arrête le scheduler."""
    if scheduler.running:
        scheduler.shutdown(wait=False)
        logger.info("DCA scheduler stopped")
