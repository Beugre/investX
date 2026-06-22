"""
Script one-shot : annule tous les abonnements Stripe actifs.
Usage :
    STRIPE_SECRET_KEY=sk_live_xxx python scripts/cancel_all_subscriptions.py [--dry-run]
"""
import os
import sys
import argparse

try:
    import stripe
except ImportError:
    print("Installer stripe : pip install stripe")
    sys.exit(1)


def main():
    parser = argparse.ArgumentParser(description="Annule tous les abonnements Stripe actifs.")
    parser.add_argument("--dry-run", action="store_true", help="Affiche sans annuler.")
    args = parser.parse_args()

    api_key = os.environ.get("STRIPE_SECRET_KEY")
    if not api_key:
        print("Erreur : variable STRIPE_SECRET_KEY manquante.")
        sys.exit(1)

    stripe.api_key = api_key

    statuses = ["active", "past_due", "trialing"]
    to_cancel = []

    print("Récupération des abonnements...")
    for status in statuses:
        page = stripe.Subscription.list(status=status, limit=100)
        while True:
            for sub in page.data:
                to_cancel.append(sub)
            if not page.has_more:
                break
            page = stripe.Subscription.list(
                status=status, limit=100, starting_after=page.data[-1].id
            )

    if not to_cancel:
        print("Aucun abonnement actif trouvé.")
        return

    print(f"\n{len(to_cancel)} abonnement(s) trouvé(s) :")
    for sub in to_cancel:
        customer = sub.customer
        period_end = sub.current_period_end
        print(f"  - {sub.id}  customer={customer}  status={sub.status}  ends={period_end}")

    if args.dry_run:
        print("\n[DRY RUN] Aucune action effectuée.")
        return

    confirm = input(f"\nAnnuler ces {len(to_cancel)} abonnement(s) ? (oui/non) : ").strip().lower()
    if confirm not in ("oui", "o", "yes", "y"):
        print("Annulation abandonnée.")
        return

    errors = []
    for sub in to_cancel:
        try:
            # cancel_at_period_end=False = annulation immédiate
            stripe.Subscription.cancel(sub.id)
            print(f"  ✓ Annulé : {sub.id}")
        except stripe.error.StripeError as e:
            print(f"  ✗ Erreur {sub.id} : {e}")
            errors.append((sub.id, str(e)))

    print(f"\nTerminé. {len(to_cancel) - len(errors)} annulé(s), {len(errors)} erreur(s).")
    if errors:
        for sid, err in errors:
            print(f"  - {sid} : {err}")


if __name__ == "__main__":
    main()
