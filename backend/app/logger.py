"""
Logger centralisé pour l'application InvestX.
"""

import logging
import sys

from app.config import settings


def get_logger(name: str) -> logging.Logger:
    """Retourne un logger configuré avec le niveau défini dans les settings."""
    logger = logging.getLogger(name)
    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        formatter = logging.Formatter(
            "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)
    logger.setLevel(getattr(logging, settings.log_level.upper(), logging.INFO))
    return logger
