"""
Validateurs réutilisables.
"""

from __future__ import annotations

from app.core.constants import ALLOWED_SYMBOLS


def is_valid_symbol(symbol: str) -> bool:
    """Vérifie si un symbole est dans la whitelist."""
    return symbol in ALLOWED_SYMBOLS


def validate_symbol_or_raise(symbol: str) -> str:
    """Valide et retourne le symbole, ou lève une ValueError."""
    if not is_valid_symbol(symbol):
        raise ValueError(f"Invalid symbol: {symbol}. Allowed: {ALLOWED_SYMBOLS}")
    return symbol
