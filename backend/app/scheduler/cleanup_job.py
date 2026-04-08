"""
Job de nettoyage : supprime les locks et spending records anciens.
Tourne une fois par jour.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from firebase_admin import firestore as fb_firestore

from app.logger import get_logger

logger = get_logger(__name__)


def cleanup_old_records_job() -> None:
    """Supprime les dca_locks > 7 jours et stripe_events > 30 jours."""
    try:
        db = fb_firestore.client()
        deleted = 0

        # Locks plus vieux que 7 jours
        cutoff_locks = datetime.now(timezone.utc) - timedelta(days=7)
        old_locks = (
            db.collection("dca_locks")
            .where("locked_at", "<", cutoff_locks)
            .limit(500)
            .stream()
        )
        for doc in old_locks:
            doc.reference.delete()
            deleted += 1

        # Stripe events plus vieux que 30 jours
        cutoff_events = datetime.now(timezone.utc) - timedelta(days=30)
        old_events = (
            db.collection("stripe_events")
            .where("processed_at", "<", cutoff_events)
            .limit(500)
            .stream()
        )
        for doc in old_events:
            doc.reference.delete()
            deleted += 1

        if deleted:
            logger.info("Cleanup: %d old records deleted", deleted)
    except Exception as e:
        logger.error("Cleanup job failed: %s", e)
