"""
Jobs planifiés – wrapper pour le scheduler.
"""

from app.services.dca_service import run_cycle
from app.logger import get_logger

logger = get_logger(__name__)


def dca_job() -> None:
    """Job de cycle DCA, appelé par le scheduler."""
    try:
        executed = run_cycle()
        logger.info("DCA job completed: %d orders executed", executed)
    except Exception as e:
        logger.error("DCA job failed: %s", e)
