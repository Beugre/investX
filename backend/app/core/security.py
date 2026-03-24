"""
Utilitaires de sécurité (hashing, validation, etc.)
"""

from __future__ import annotations


def mask_secret(value: str, visible: int = 4) -> str:
    """Masque un secret en ne laissant que les derniers caractères visibles."""
    if len(value) <= visible:
        return "***"
    return "*" * (len(value) - visible) + value[-visible:]
