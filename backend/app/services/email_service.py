"""
Service Email – envoi de notifications par email (SMTP SSL).
"""

from __future__ import annotations

import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from datetime import datetime

import pytz

from app.logger import get_logger

logger = get_logger(__name__)

SMTP_HOST = os.getenv("SMTP_HOST", "mail.investxbot.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", "465"))
SMTP_USER = os.getenv("SMTP_USER", "contact@investxbot.com")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")
SMTP_FROM = os.getenv("SMTP_FROM", "InvestX <contact@investxbot.com>")


def _send_email(to: str, subject: str, html_body: str) -> bool:
    """Envoie un email via SMTP SSL. Retourne True si succès."""
    if not SMTP_PASSWORD:
        logger.warning("SMTP_PASSWORD not configured, skipping email")
        return False

    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = SMTP_FROM
        msg["To"] = to
        msg.attach(MIMEText(html_body, "html", "utf-8"))

        with smtplib.SMTP_SSL(SMTP_HOST, SMTP_PORT, timeout=15) as server:
            server.login(SMTP_USER, SMTP_PASSWORD)
            server.sendmail(SMTP_USER, to, msg.as_string())

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
    fees = order.get("fees_usd", 0)
    status = order.get("status", "?")
    now = datetime.now(pytz.timezone("Europe/Paris")).strftime("%d/%m/%Y à %H:%M")

    subject = f"✅ Achat DCA exécuté – {symbol}"

    html = f"""
    <div style="font-family: 'Segoe UI', Arial, sans-serif; max-width: 600px; margin: 0 auto; background: #0e1117; color: #fafafa; border-radius: 12px; overflow: hidden;">
        <div style="background: linear-gradient(135deg, #1a73e8, #00c853); padding: 24px; text-align: center;">
            <h1 style="margin: 0; font-size: 22px; color: #fff;">✅ Achat DCA exécuté</h1>
        </div>
        <div style="padding: 24px;">
            <table style="width: 100%; border-collapse: collapse; margin-bottom: 20px;">
                <tr>
                    <td style="padding: 10px 0; border-bottom: 1px solid #333; color: #aaa;">Paire</td>
                    <td style="padding: 10px 0; border-bottom: 1px solid #333; text-align: right; font-weight: bold;">{symbol}</td>
                </tr>
                <tr>
                    <td style="padding: 10px 0; border-bottom: 1px solid #333; color: #aaa;">Montant investi</td>
                    <td style="padding: 10px 0; border-bottom: 1px solid #333; text-align: right; font-weight: bold;">{amount:.2f} $</td>
                </tr>
                <tr>
                    <td style="padding: 10px 0; border-bottom: 1px solid #333; color: #aaa;">Quantité reçue</td>
                    <td style="padding: 10px 0; border-bottom: 1px solid #333; text-align: right; font-weight: bold;">{quantity:.8f}</td>
                </tr>
                <tr>
                    <td style="padding: 10px 0; border-bottom: 1px solid #333; color: #aaa;">Prix unitaire</td>
                    <td style="padding: 10px 0; border-bottom: 1px solid #333; text-align: right; font-weight: bold;">{price:,.2f} $</td>
                </tr>
                <tr>
                    <td style="padding: 10px 0; border-bottom: 1px solid #333; color: #aaa;">Frais</td>
                    <td style="padding: 10px 0; border-bottom: 1px solid #333; text-align: right;">{fees:.4f} $</td>
                </tr>
                <tr>
                    <td style="padding: 10px 0; color: #aaa;">Statut</td>
                    <td style="padding: 10px 0; text-align: right; color: #00c853; font-weight: bold;">{status}</td>
                </tr>
            </table>
            <p style="color: #888; font-size: 12px; text-align: center;">{now} (Europe/Paris)</p>
        </div>
        <div style="background: #161b22; padding: 16px; text-align: center;">
            <a href="https://investxbot.com/Dashboard" style="color: #1a73e8; text-decoration: none; font-size: 14px;">📊 Voir mon dashboard</a>
            <p style="color: #555; font-size: 11px; margin-top: 10px;">InvestX – DCA Crypto Automatisé</p>
        </div>
    </div>
    """

    return _send_email(to, subject, html)


def send_v2_order_email(
    to: str,
    rsi: float, rsi_label: str, regime: str,
    btc_amount: float, eth_amount: float,
    crash_amount: float, crash_levels: list[str],
    orders: list[dict],
) -> bool:
    """Envoie un email récapitulatif d'un cycle DCA RSI v2."""
    now = datetime.now(pytz.timezone("Europe/Paris")).strftime("%d/%m/%Y à %H:%M")
    total = btc_amount + eth_amount + crash_amount

    orders_rows = ""
    for o in orders:
        orders_rows += f"""
        <tr>
            <td style="padding: 8px; border-bottom: 1px solid #333;">{o.get('symbol', '?')}</td>
            <td style="padding: 8px; border-bottom: 1px solid #333; text-align: right;">{o.get('amount_eur', 0):.2f} $</td>
            <td style="padding: 8px; border-bottom: 1px solid #333; text-align: right;">{o.get('quantity', 0):.8f}</td>
            <td style="padding: 8px; border-bottom: 1px solid #333; text-align: right;">{o.get('price', 0):,.2f} $</td>
        </tr>
        """

    crash_html = ""
    if crash_amount > 0:
        crash_html = f"""
        <div style="background: #2d1a1a; border: 1px solid #e53935; border-radius: 8px; padding: 12px; margin: 12px 0;">
            <strong style="color: #e53935;">🚨 Crash Reserve : {crash_amount:.2f} $</strong>
            <br><span style="color: #aaa;">Niveaux : {', '.join(crash_levels)}</span>
        </div>
        """

    subject = f"📊 DCA RSI v2 – RSI {rsi:.0f} ({rsi_label}) – {total:.2f} $"

    html = f"""
    <div style="font-family: 'Segoe UI', Arial, sans-serif; max-width: 600px; margin: 0 auto; background: #0e1117; color: #fafafa; border-radius: 12px; overflow: hidden;">
        <div style="background: linear-gradient(135deg, #1a73e8, #00c853); padding: 24px; text-align: center;">
            <h1 style="margin: 0; font-size: 22px; color: #fff;">📊 DCA RSI v2 exécuté</h1>
        </div>
        <div style="padding: 24px;">
            <div style="display: flex; justify-content: space-between; margin-bottom: 16px;">
                <div style="background: #161b22; border-radius: 8px; padding: 12px; flex: 1; margin-right: 8px; text-align: center;">
                    <div style="color: #aaa; font-size: 12px;">RSI</div>
                    <div style="font-size: 24px; font-weight: bold;">{rsi:.1f}</div>
                    <div style="color: #1a73e8; font-size: 13px;">{rsi_label}</div>
                </div>
                <div style="background: #161b22; border-radius: 8px; padding: 12px; flex: 1; margin-left: 8px; text-align: center;">
                    <div style="color: #aaa; font-size: 12px;">Régime</div>
                    <div style="font-size: 18px; font-weight: bold; margin-top: 4px;">{regime}</div>
                </div>
            </div>

            <table style="width: 100%; border-collapse: collapse; margin-bottom: 12px;">
                <tr style="border-bottom: 2px solid #333;">
                    <td style="padding: 8px; color: #aaa; font-size: 13px;">Paire</td>
                    <td style="padding: 8px; color: #aaa; font-size: 13px; text-align: right;">Montant</td>
                    <td style="padding: 8px; color: #aaa; font-size: 13px; text-align: right;">Quantité</td>
                    <td style="padding: 8px; color: #aaa; font-size: 13px; text-align: right;">Prix</td>
                </tr>
                {orders_rows}
            </table>

            {crash_html}

            <div style="background: #161b22; border-radius: 8px; padding: 16px; text-align: center; margin-top: 12px;">
                <span style="color: #aaa;">Total investi :</span>
                <span style="font-size: 22px; font-weight: bold; color: #00c853; margin-left: 8px;">{total:.2f} $</span>
            </div>

            <p style="color: #888; font-size: 12px; text-align: center; margin-top: 16px;">{now} (Europe/Paris)</p>
        </div>
        <div style="background: #161b22; padding: 16px; text-align: center;">
            <a href="https://investxbot.com/Dashboard" style="color: #1a73e8; text-decoration: none; font-size: 14px;">📊 Voir mon dashboard</a>
            <p style="color: #555; font-size: 11px; margin-top: 10px;">InvestX – DCA Crypto Automatisé</p>
        </div>
    </div>
    """

    return _send_email(to, subject, html)


def send_error_email(to: str, error_message: str) -> bool:
    """Envoie un email de notification d'erreur."""
    now = datetime.now(pytz.timezone("Europe/Paris")).strftime("%d/%m/%Y à %H:%M")
    subject = "❌ Erreur DCA – InvestX"

    html = f"""
    <div style="font-family: 'Segoe UI', Arial, sans-serif; max-width: 600px; margin: 0 auto; background: #0e1117; color: #fafafa; border-radius: 12px; overflow: hidden;">
        <div style="background: #e53935; padding: 24px; text-align: center;">
            <h1 style="margin: 0; font-size: 22px; color: #fff;">❌ Erreur DCA</h1>
        </div>
        <div style="padding: 24px;">
            <div style="background: #2d1a1a; border: 1px solid #e53935; border-radius: 8px; padding: 16px;">
                <p style="margin: 0; line-height: 1.6;">{error_message}</p>
            </div>
            <p style="color: #888; font-size: 12px; text-align: center; margin-top: 16px;">{now} (Europe/Paris)</p>
        </div>
        <div style="background: #161b22; padding: 16px; text-align: center;">
            <a href="https://investxbot.com/Dashboard" style="color: #1a73e8; text-decoration: none; font-size: 14px;">📊 Voir mon dashboard</a>
            <p style="color: #555; font-size: 11px; margin-top: 10px;">InvestX – DCA Crypto Automatisé</p>
        </div>
    </div>
    """

    return _send_email(to, subject, html)
