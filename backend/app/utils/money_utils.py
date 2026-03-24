"""
Utilitaires monétaires.
"""

from __future__ import annotations

from decimal import Decimal, ROUND_HALF_UP


def round_eur(value: float, decimals: int = 2) -> float:
    """Arrondit un montant EUR."""
    return float(Decimal(str(value)).quantize(Decimal(10) ** -decimals, rounding=ROUND_HALF_UP))


def format_eur(value: float) -> str:
    """Formate un montant EUR pour affichage."""
    return f"{value:,.2f} €"
