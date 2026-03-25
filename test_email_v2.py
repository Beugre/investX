import sys, os
sys.path.insert(0, "/opt/investx/backend")
from dotenv import load_dotenv
load_dotenv("/opt/investx/backend/.env")

import app.services.email_service as es
# Reload env vars into module
es.SMTP_HOST = os.getenv("SMTP_HOST", "")
es.SMTP_PORT = int(os.getenv("SMTP_PORT", "465"))
es.SMTP_USER = os.getenv("SMTP_USER", "")
es.SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")
es.SMTP_FROM = os.getenv("SMTP_FROM", "")

print(f"Host={es.SMTP_HOST} Port={es.SMTP_PORT} User={es.SMTP_USER} Pwd={'***' if es.SMTP_PASSWORD else 'MISSING'} From={es.SMTP_FROM}")

# Test v2 order email
result = es.send_v2_order_email(
    to="yoann.beugre@gmail.com",
    rsi=28.5,
    rsi_label="Survente",
    regime="bear",
    btc_amount=30.83,
    eth_amount=31.03,
    crash_amount=0.0,
    crash_levels=[],
    orders=[
        {"symbol": "BTCUSDC", "side": "BUY", "qty": 0.00045, "price": 68500.0, "cost": 30.83},
        {"symbol": "ETHUSDC", "side": "BUY", "qty": 0.0085, "price": 3650.0, "cost": 31.03},
    ],
)
print(f"Email sent: {result}")
