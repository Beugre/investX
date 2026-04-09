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
    """Supprime les dca_locks > 7 jours, stripe_events > 30 jours,
    et prune les snapshots portfolio (max 100 par utilisateur)."""
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

        # Prune portfolio snapshots (max 100 par utilisateur)
        try:
            users = db.collection("users").stream()
            for user_doc in users:
                uid = user_doc.id
                coll = db.collection("users").document(uid).collection("portfolio_snapshots")
                old_snaps = list(
                    coll.order_by("captured_at", direction=fb_firestore.Query.DESCENDING)
                    .offset(100)
                    .limit(500)
                    .stream()
                )
                if old_snaps:
                    batch = db.batch()
                    for doc in old_snaps:
                        batch.delete(doc.reference)
                    batch.commit()
                    deleted += len(old_snaps)
                    logger.info("Pruned %d old snapshots for user %s", len(old_snaps), uid)
        except Exception as e:
            logger.error("Snapshot pruning failed: %s", e)

        if deleted:
            logger.info("Cleanup: %d old records deleted", deleted)
    except Exception as e:
        logger.error("Cleanup job failed: %s", e)
