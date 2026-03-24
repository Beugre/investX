"""
Verrous anti-double exécution pour le scheduler DCA.
Utilise une idempotency key basée sur uid + date + symbol.
"""

from __future__ import annotations

from datetime import datetime

import pytz
from firebase_admin import firestore as fb_firestore


def _db():
    return fb_firestore.client()


def acquire_lock(uid: str, symbol: str, date_str: str | None = None) -> bool:
    """Tente d'acquérir un verrou pour éviter la double exécution.
    Retourne True si le verrou a été acquis (pas encore exécuté).
    """
    if date_str is None:
        date_str = datetime.now(pytz.timezone("Europe/Paris")).strftime("%Y-%m-%d")

    lock_id = f"{uid}_{symbol}_{date_str}"
    lock_ref = _db().collection("dca_locks").document(lock_id)

    # Transaction pour atomicité
    @fb_firestore.transactional
    def _try_acquire(transaction):
        doc = lock_ref.get(transaction=transaction)
        if doc.exists:
            return False  # Déjà exécuté
        transaction.set(lock_ref, {
            "uid": uid,
            "symbol": symbol,
            "date": date_str,
            "locked_at": datetime.now(pytz.UTC),
        })
        return True

    transaction = _db().transaction()
    return _try_acquire(transaction)


def release_lock(uid: str, symbol: str, date_str: str | None = None) -> None:
    """Libère un verrou (en cas d'erreur, pour réessayer)."""
    if date_str is None:
        date_str = datetime.now(pytz.timezone("Europe/Paris")).strftime("%Y-%m-%d")

    lock_id = f"{uid}_{symbol}_{date_str}"
    _db().collection("dca_locks").document(lock_id).delete()
