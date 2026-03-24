"""
Utilitaires datetime.
"""

from __future__ import annotations

from datetime import datetime

import pytz

from app.core.constants import DEFAULT_TIMEZONE


def now_paris() -> datetime:
    """Retourne l'heure actuelle en Europe/Paris."""
    return datetime.now(pytz.timezone(DEFAULT_TIMEZONE))


def utc_now() -> datetime:
    """Retourne l'heure actuelle en UTC."""
    return datetime.now(pytz.UTC)


def to_timezone(dt: datetime, tz_name: str = DEFAULT_TIMEZONE) -> datetime:
    """Convertit un datetime vers une timezone."""
    tz = pytz.timezone(tz_name)
    return dt.astimezone(tz)
