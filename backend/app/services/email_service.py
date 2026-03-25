"""
Service Email – envoi de notifications par email (Brevo SMTP relay).
"""

from __future__ import annotations

import os
import ssl
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from datetime import datetime

import pytz

from app.logger import get_logger

logger = get_logger(__name__)

SMTP_HOST = os.getenv("SMTP_HOST", "smtp-relay.brevo.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER = os.getenv("SMTP_USER", "")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")
SMTP_FROM = os.getenv("SMTP_FROM", "InvestX <contact@investxbot.com>")


def _send_email(to: str, subject: str, html_body: str, plain_body: str = "") -> bool:
    """Envoie un email via Brevo SMTP (STARTTLS 587). Retourne True si succès."""
    if not SMTP_PASSWORD:
        logger.warning("SMTP_PASSWORD not configured, skipping email")
        return False

    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = SMTP_FROM
        msg["To"] = to
        msg["Reply-To"] = "contact@investxbot.com"

        # Texte brut (fallback + meilleure délivrabilité)
        if plain_body:
            msg.attach(MIMEText(plain_body, "plain", "utf-8"))
        # HTML
        msg.attach(MIMEText(html_body, "html", "utf-8"))

        with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=15) as server:
            server.starttls()
            server.login(SMTP_USER, SMTP_PASSWORD)
            server.sendmail(SMTP_FROM, to, msg.as_string())

        logger.info("Email sent to %s: %s", to, subject)
        return True
    except Exception as e:
        logger.error("Failed to send email to %s: %s", to, e)
        return False


def send_order_email(to: str, order: dict) -> bool:
    """Envoie un email de confirmation d'achat DCA."""
    symbol = order.get("symbol", "?")
    amount = order.get("amount_eur", 0)
    quantity = order.get("quantity", 0)
    price = order.get("price", 0)
    fees = order.get("commission", order.get("fees_usd", 0))
    status = order.get("status", "?")
    order_type = order.get("order_type", "market")
    estimated = order.get("estimated", False)
    now = datetime.now(pytz.timezone("Europe/Paris")).strftime("%d %B %Y %H:%M GMT")

    # Déterminer devise et pair display selon le format du symbole
    is_eur = "-EUR" in symbol
    cs = "€" if is_eur else "$"
    currency_name = "EUR" if is_eur else "USD"

    # Extraire la base currency
    if "-" in symbol:
        base = symbol.split("-")[0]
        pair_display = symbol
    else:
        base = symbol.replace("USDC", "").replace("USDT", "").replace("EUR", "")
        pair_display = f"{base}-USDC"

    # Type d'ordre affiché
    type_label = "Maker · Achat (0 % frais)" if order_type == "maker" else "Taker · Achat"
    est_label = " (estimé)" if estimated else ""

    subject = f"Ordre d'achat de {pair_display} exécuté"

    plain = (
        f"InvestX\n\n"
        f"Ordre d'achat de {pair_display} exécuté\n\n"
        f"Votre ordre d'achat de {quantity:.8f} {base} au prix de "
        f"{price:,.2f} {cs} a été exécuté.\n\n"
        f"Date d'exécution : {now}\n"
        f"Type : {type_label}\n"
        f"Prix d'exécution moyen : {price:,.2f} {cs}{est_label}\n"
        f"Quantité exécutée : {quantity:.8f} {base}{est_label}\n"
        f"Frais : {fees:.4f} {cs}\n"
        f"Valeur exécutée : {amount:.2f} {cs}\n"
        f"Montant reçu : {quantity:.8f} {base}\n\n"
        f"Voir sur InvestX : https://investxbot.com/Dashboard"
    )

    html = f"""
<!DOCTYPE html>
<html><head><meta charset="utf-8"></head>
<body style="margin:0;padding:0;background-color:#f5f5f5;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,Helvetica,Arial,sans-serif;">
<table width="100%" cellpadding="0" cellspacing="0" style="background-color:#f5f5f5;padding:40px 0;">
<tr><td align="center">
<table width="600" cellpadding="0" cellspacing="0" style="background-color:#ffffff;border-radius:12px;overflow:hidden;box-shadow:0 2px 8px rgba(0,0,0,0.06);">

  <!-- Header -->
  <tr><td style="padding:32px 40px 0;text-align:center;">
    <p style="margin:0;font-size:16px;font-weight:600;color:#1a1a2e;letter-spacing:1px;">InvestX</p>
  </td></tr>

  <!-- Title -->
  <tr><td style="padding:24px 40px 0;text-align:center;">
    <h1 style="margin:0;font-size:28px;font-weight:800;color:#1a1a2e;line-height:1.3;">Ordre d'achat de {pair_display} exécuté</h1>
  </td></tr>

  <!-- Subtitle -->
  <tr><td style="padding:16px 40px 0;text-align:center;">
    <p style="margin:0;font-size:15px;color:#666;line-height:1.5;">
      Votre ordre d'achat de {quantity:.8f} {base} au prix de<br>{price:,.2f} {cs} a été exécuté.
    </p>
  </td></tr>

  <!-- Details table -->
  <tr><td style="padding:28px 40px;">
    <table width="100%" cellpadding="0" cellspacing="0" style="border:1px solid #e8e8e8;border-radius:8px;overflow:hidden;">
      <tr>
        <td style="padding:14px 16px;font-size:14px;color:#888;border-bottom:1px solid #f0f0f0;">Date d'exécution</td>
        <td style="padding:14px 16px;font-size:14px;color:#1a1a2e;font-weight:600;text-align:right;border-bottom:1px solid #f0f0f0;">{now}</td>
      </tr>
      <tr>
        <td style="padding:14px 16px;font-size:14px;color:#888;border-bottom:1px solid #f0f0f0;">Type</td>
        <td style="padding:14px 16px;font-size:14px;color:#1a1a2e;font-weight:600;text-align:right;border-bottom:1px solid #f0f0f0;">{type_label}</td>
      </tr>
      <tr>
        <td style="padding:14px 16px;font-size:14px;color:#888;border-bottom:1px solid #f0f0f0;">Prix d'exécution moyen</td>
        <td style="padding:14px 16px;font-size:14px;color:#1a1a2e;font-weight:600;text-align:right;border-bottom:1px solid #f0f0f0;">{price:,.2f} {cs}{est_label}</td>
      </tr>
      <tr>
        <td style="padding:14px 16px;font-size:14px;color:#888;border-bottom:1px solid #f0f0f0;">Quantité exécutée</td>
        <td style="padding:14px 16px;font-size:14px;color:#1a1a2e;font-weight:600;text-align:right;border-bottom:1px solid #f0f0f0;">{quantity:.8f} {base}{est_label}</td>
      </tr>
      <tr>
        <td style="padding:14px 16px;font-size:14px;color:#888;border-bottom:1px solid #f0f0f0;">Frais</td>
        <td style="padding:14px 16px;font-size:14px;color:#1a1a2e;font-weight:600;text-align:right;border-bottom:1px solid #f0f0f0;">{fees:.4f} {cs}</td>
      </tr>
      <tr>
        <td style="padding:14px 16px;font-size:14px;color:#888;border-bottom:1px solid #f0f0f0;">Valeur exécutée</td>
        <td style="padding:14px 16px;font-size:14px;color:#1a1a2e;font-weight:600;text-align:right;border-bottom:1px solid #f0f0f0;">{amount:.2f} {cs}</td>
      </tr>
      <tr>
        <td style="padding:14px 16px;font-size:14px;color:#888;">Montant reçu</td>
        <td style="padding:14px 16px;font-size:14px;color:#1a1a2e;font-weight:600;text-align:right;">{quantity:.8f} {base}</td>
      </tr>
    </table>
  </td></tr>

  <!-- CTA Button -->
  <tr><td style="padding:0 40px 36px;text-align:center;">
    <a href="https://investxbot.com/Dashboard" style="display:inline-block;padding:14px 32px;background-color:#1a73e8;color:#ffffff;text-decoration:none;border-radius:24px;font-size:15px;font-weight:600;">Afficher sur InvestX</a>
  </td></tr>

</table>
</td></tr>
</table>
</body></html>
"""

    return _send_email(to, subject, html, plain)


def send_v2_order_email(
    to: str,
    rsi: float, rsi_label: str, regime: str,
    btc_amount: float, eth_amount: float,
    crash_amount: float, crash_levels: list[str],
    orders: list[dict],
) -> bool:
    """Envoie un email récapitulatif d'un cycle DCA RSI v2."""
    now = datetime.now(pytz.timezone("Europe/Paris")).strftime("%d %B %Y %H:%M GMT")
    total = btc_amount + eth_amount + crash_amount

    # Détecter devise à partir des ordres
    any_eur = any("EUR" in o.get("symbol", "") for o in orders)
    cs = "€" if any_eur else "$"
    currency_name = "EUR" if any_eur else "USD"

    # Build order rows
    orders_rows = ""
    plain_orders = ""
    for o in orders:
        sym = o.get("symbol", "?")
        is_eur = "-EUR" in sym
        o_cs = "€" if is_eur else "$"

        if "-" in sym:
            base = sym.split("-")[0]
            pair = sym
        else:
            base = sym.replace("USDC", "").replace("USDT", "").replace("EUR", "")
            pair = f"{base}-USDC"

        qty = o.get("quantity", 0)
        px = o.get("price", 0)
        amt = o.get("amount_eur", 0)
        fees = o.get("commission", o.get("fees_usd", 0))
        order_type = o.get("order_type", "market")
        estimated = o.get("estimated", False)
        type_label = "Maker (0 %)" if order_type == "maker" else "Taker"
        est_label = " (estimé)" if estimated else ""

        orders_rows += f"""
      <tr>
        <td style="padding:14px 16px;font-size:14px;color:#888;border-bottom:1px solid #f0f0f0;">Paire</td>
        <td style="padding:14px 16px;font-size:14px;color:#1a1a2e;font-weight:600;text-align:right;border-bottom:1px solid #f0f0f0;">{pair} · {type_label}</td>
      </tr>
      <tr>
        <td style="padding:14px 16px;font-size:14px;color:#888;border-bottom:1px solid #f0f0f0;">Prix d'exécution moyen</td>
        <td style="padding:14px 16px;font-size:14px;color:#1a1a2e;font-weight:600;text-align:right;border-bottom:1px solid #f0f0f0;">{px:,.2f} {o_cs}{est_label}</td>
      </tr>
      <tr>
        <td style="padding:14px 16px;font-size:14px;color:#888;border-bottom:1px solid #f0f0f0;">Quantité exécutée</td>
        <td style="padding:14px 16px;font-size:14px;color:#1a1a2e;font-weight:600;text-align:right;border-bottom:1px solid #f0f0f0;">{qty:.8f} {base}{est_label}</td>
      </tr>
      <tr>
        <td style="padding:14px 16px;font-size:14px;color:#888;border-bottom:1px solid #f0f0f0;">Frais</td>
        <td style="padding:14px 16px;font-size:14px;color:#1a1a2e;font-weight:600;text-align:right;border-bottom:1px solid #f0f0f0;">{fees:.4f} {o_cs}</td>
      </tr>
      <tr>
        <td style="padding:14px 16px;font-size:14px;color:#888;border-bottom:1px solid #f0f0f0;">Valeur exécutée</td>
        <td style="padding:14px 16px;font-size:14px;color:#1a1a2e;font-weight:600;text-align:right;border-bottom:1px solid #f0f0f0;">{amt:.2f} {o_cs}</td>
      </tr>
      <tr>
        <td style="padding:14px 16px;font-size:14px;color:#888;border-bottom:1px solid #e8e8e8;">Montant reçu</td>
        <td style="padding:14px 16px;font-size:14px;color:#1a1a2e;font-weight:600;text-align:right;border-bottom:1px solid #e8e8e8;">{qty:.8f} {base}</td>
      </tr>
"""
        plain_orders += f"  {pair} ({type_label}): {qty:.8f} @ {px:,.2f} {o_cs} = {amt:.2f} {o_cs}\n"

    crash_row = ""
    crash_plain = ""
    if crash_amount > 0:
        crash_row = f"""
      <tr>
        <td style="padding:14px 16px;font-size:14px;color:#e53935;font-weight:600;border-bottom:1px solid #f0f0f0;">Crash Reserve</td>
        <td style="padding:14px 16px;font-size:14px;color:#e53935;font-weight:600;text-align:right;border-bottom:1px solid #f0f0f0;">{crash_amount:.2f} {cs} ({', '.join(crash_levels)})</td>
      </tr>
"""
        crash_plain = f"  Crash Reserve: {crash_amount:.2f} {cs} ({', '.join(crash_levels)})\n"

    subject = f"Ordres DCA RSI v2 exécutés – {total:.2f} {cs}"

    plain = (
        f"InvestX\n\n"
        f"Ordres DCA RSI v2 exécutés\n\n"
        f"RSI : {rsi:.1f} ({rsi_label}) | Régime : {regime}\n\n"
        f"Ordres :\n{plain_orders}{crash_plain}"
        f"\nTotal investi : {total:.2f} {cs}\n"
        f"Date : {now}\n\n"
        f"Voir sur InvestX : https://investxbot.com/Dashboard"
    )

    html = f"""
<!DOCTYPE html>
<html><head><meta charset="utf-8"></head>
<body style="margin:0;padding:0;background-color:#f5f5f5;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,Helvetica,Arial,sans-serif;">
<table width="100%" cellpadding="0" cellspacing="0" style="background-color:#f5f5f5;padding:40px 0;">
<tr><td align="center">
<table width="600" cellpadding="0" cellspacing="0" style="background-color:#ffffff;border-radius:12px;overflow:hidden;box-shadow:0 2px 8px rgba(0,0,0,0.06);">

  <!-- Header -->
  <tr><td style="padding:32px 40px 0;text-align:center;">
    <p style="margin:0;font-size:16px;font-weight:600;color:#1a1a2e;letter-spacing:1px;">InvestX</p>
  </td></tr>

  <!-- Title -->
  <tr><td style="padding:24px 40px 0;text-align:center;">
    <h1 style="margin:0;font-size:26px;font-weight:800;color:#1a1a2e;line-height:1.3;">Ordres DCA RSI v2 exécutés</h1>
  </td></tr>

  <!-- Subtitle -->
  <tr><td style="padding:16px 40px 0;text-align:center;">
    <p style="margin:0;font-size:15px;color:#666;line-height:1.5;">
      RSI : {rsi:.1f} ({rsi_label}) · Régime : {regime}<br>
      Total investi : <strong>{total:.2f} {cs}</strong>
    </p>
  </td></tr>

  <!-- Details table -->
  <tr><td style="padding:28px 40px;">
    <table width="100%" cellpadding="0" cellspacing="0" style="border:1px solid #e8e8e8;border-radius:8px;overflow:hidden;">
      <tr>
        <td style="padding:14px 16px;font-size:14px;color:#888;border-bottom:1px solid #f0f0f0;">Date d'exécution</td>
        <td style="padding:14px 16px;font-size:14px;color:#1a1a2e;font-weight:600;text-align:right;border-bottom:1px solid #f0f0f0;">{now}</td>
      </tr>
      <tr>
        <td style="padding:14px 16px;font-size:14px;color:#888;border-bottom:1px solid #f0f0f0;">Stratégie</td>
        <td style="padding:14px 16px;font-size:14px;color:#1a1a2e;font-weight:600;text-align:right;border-bottom:1px solid #f0f0f0;">DCA RSI v2</td>
      </tr>
      <tr>
        <td style="padding:14px 16px;font-size:14px;color:#888;border-bottom:1px solid #e8e8e8;">RSI / Régime</td>
        <td style="padding:14px 16px;font-size:14px;color:#1a1a2e;font-weight:600;text-align:right;border-bottom:1px solid #e8e8e8;">{rsi:.1f} ({rsi_label}) · {regime}</td>
      </tr>
      {orders_rows}
      {crash_row}
      <tr>
        <td style="padding:14px 16px;font-size:14px;color:#1a1a2e;font-weight:700;">Total investi</td>
        <td style="padding:14px 16px;font-size:14px;color:#1a1a2e;font-weight:700;text-align:right;">{total:.2f} {cs}</td>
      </tr>
    </table>
  </td></tr>

  <!-- CTA Button -->
  <tr><td style="padding:0 40px 36px;text-align:center;">
    <a href="https://investxbot.com/Dashboard" style="display:inline-block;padding:14px 32px;background-color:#1a73e8;color:#ffffff;text-decoration:none;border-radius:24px;font-size:15px;font-weight:600;">Afficher sur InvestX</a>
  </td></tr>

</table>
</td></tr>
</table>
</body></html>
"""

    return _send_email(to, subject, html, plain)


def send_error_email(to: str, error_message: str) -> bool:
    """Envoie un email de notification d'erreur."""
    now = datetime.now(pytz.timezone("Europe/Paris")).strftime("%d %B %Y %H:%M GMT")
    subject = "Erreur DCA - InvestX"

    plain = (
        f"InvestX\n\n"
        f"Erreur DCA\n\n"
        f"{error_message}\n\n"
        f"Date : {now}\n\n"
        f"Voir sur InvestX : https://investxbot.com/Dashboard"
    )

    html = f"""
<!DOCTYPE html>
<html><head><meta charset="utf-8"></head>
<body style="margin:0;padding:0;background-color:#f5f5f5;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,Helvetica,Arial,sans-serif;">
<table width="100%" cellpadding="0" cellspacing="0" style="background-color:#f5f5f5;padding:40px 0;">
<tr><td align="center">
<table width="600" cellpadding="0" cellspacing="0" style="background-color:#ffffff;border-radius:12px;overflow:hidden;box-shadow:0 2px 8px rgba(0,0,0,0.06);">

  <!-- Header -->
  <tr><td style="padding:32px 40px 0;text-align:center;">
    <p style="margin:0;font-size:16px;font-weight:600;color:#1a1a2e;letter-spacing:1px;">InvestX</p>
  </td></tr>

  <!-- Title -->
  <tr><td style="padding:24px 40px 0;text-align:center;">
    <h1 style="margin:0;font-size:26px;font-weight:800;color:#e53935;line-height:1.3;">Erreur DCA</h1>
  </td></tr>

  <!-- Error message -->
  <tr><td style="padding:24px 40px;">
    <table width="100%" cellpadding="0" cellspacing="0" style="border:1px solid #fce4e4;border-radius:8px;overflow:hidden;background-color:#fef7f7;">
      <tr>
        <td style="padding:20px;font-size:14px;color:#c62828;line-height:1.6;">
          {error_message}
        </td>
      </tr>
    </table>
  </td></tr>

  <!-- Date -->
  <tr><td style="padding:0 40px 8px;text-align:center;">
    <p style="margin:0;font-size:13px;color:#999;">{now}</p>
  </td></tr>

  <!-- CTA Button -->
  <tr><td style="padding:16px 40px 36px;text-align:center;">
    <a href="https://investxbot.com/Dashboard" style="display:inline-block;padding:14px 32px;background-color:#1a73e8;color:#ffffff;text-decoration:none;border-radius:24px;font-size:15px;font-weight:600;">Afficher sur InvestX</a>
  </td></tr>

</table>
</td></tr>
</table>
</body></html>
"""

    return _send_email(to, subject, html, plain)


def send_welcome_email(to: str, display_name: str = "") -> bool:
    """Envoie un email de bienvenue à un nouvel utilisateur."""
    name = display_name or "investisseur"
    subject = "Bienvenue sur InvestX !"

    plain = (
        f"InvestX\n\n"
        f"Bienvenue {name} !\n\n"
        f"Votre compte InvestX a été créé avec succès.\n\n"
        f"Avec InvestX, automatisez vos investissements crypto grâce au DCA\n"
        f"(Dollar Cost Averaging) intelligent piloté par RSI.\n\n"
        f"Prochaines étapes :\n"
        f"1. Connectez vos clés API Binance\n"
        f"2. Configurez votre stratégie DCA\n"
        f"3. Activez le bot et laissez-le travailler !\n\n"
        f"Accéder au dashboard : https://investxbot.com/Dashboard\n\n"
        f"À bientôt,\nL'équipe InvestX"
    )

    html = f"""
<!DOCTYPE html>
<html><head><meta charset="utf-8"></head>
<body style="margin:0;padding:0;background-color:#f5f5f5;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,Helvetica,Arial,sans-serif;">
<table width="100%" cellpadding="0" cellspacing="0" style="background-color:#f5f5f5;padding:40px 0;">
<tr><td align="center">
<table width="600" cellpadding="0" cellspacing="0" style="background-color:#ffffff;border-radius:12px;overflow:hidden;box-shadow:0 2px 8px rgba(0,0,0,0.06);">

  <!-- Header -->
  <tr><td style="padding:32px 40px 0;text-align:center;">
    <p style="margin:0;font-size:16px;font-weight:600;color:#1a1a2e;letter-spacing:1px;">InvestX</p>
  </td></tr>

  <!-- Title -->
  <tr><td style="padding:24px 40px 0;text-align:center;">
    <h1 style="margin:0;font-size:28px;font-weight:800;color:#1a1a2e;line-height:1.3;">Bienvenue {name} !</h1>
  </td></tr>

  <!-- Subtitle -->
  <tr><td style="padding:16px 40px 0;text-align:center;">
    <p style="margin:0;font-size:15px;color:#666;line-height:1.6;">
      Votre compte InvestX a été créé avec succès.<br>
      Automatisez vos investissements crypto grâce au DCA intelligent piloté par RSI.
    </p>
  </td></tr>

  <!-- Steps -->
  <tr><td style="padding:28px 40px;">
    <table width="100%" cellpadding="0" cellspacing="0" style="border:1px solid #e8e8e8;border-radius:8px;overflow:hidden;">
      <tr>
        <td style="padding:14px 16px;font-size:14px;color:#888;border-bottom:1px solid #f0f0f0;">Étape 1</td>
        <td style="padding:14px 16px;font-size:14px;color:#1a1a2e;font-weight:600;text-align:right;border-bottom:1px solid #f0f0f0;">Connectez vos clés API Binance</td>
      </tr>
      <tr>
        <td style="padding:14px 16px;font-size:14px;color:#888;border-bottom:1px solid #f0f0f0;">Étape 2</td>
        <td style="padding:14px 16px;font-size:14px;color:#1a1a2e;font-weight:600;text-align:right;border-bottom:1px solid #f0f0f0;">Configurez votre stratégie DCA</td>
      </tr>
      <tr>
        <td style="padding:14px 16px;font-size:14px;color:#888;">Étape 3</td>
        <td style="padding:14px 16px;font-size:14px;color:#1a1a2e;font-weight:600;text-align:right;">Activez le bot et laissez-le travailler !</td>
      </tr>
    </table>
  </td></tr>

  <!-- CTA Button -->
  <tr><td style="padding:0 40px 36px;text-align:center;">
    <a href="https://investxbot.com/Dashboard" style="display:inline-block;padding:14px 32px;background-color:#1a73e8;color:#ffffff;text-decoration:none;border-radius:24px;font-size:15px;font-weight:600;">Accéder au Dashboard</a>
  </td></tr>

</table>
</td></tr>
</table>
</body></html>
"""

    return _send_email(to, subject, html, plain)
