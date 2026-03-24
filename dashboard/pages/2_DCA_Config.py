"""
Page 2 – Configuration DCA (v1 simple + v2 RSI).

Tout est configurable. Le montant journalier de base pilote l'auto-calcul
de tous les paramètres (spending caps, boost, crash reserve).
L'utilisateur peut overrider manuellement chaque valeur.
Un tableau de simulation montre le montant exécuté pour chaque scénario
RSI × MVRV (ex: accumulation forte MVRV < 1).
"""

import streamlit as st
import pandas as pd

from components.auth_guard import require_auth
from services.api_client import (
    get_dca_config,
    update_dca_config,
    get_dca_v2_config,
    update_dca_v2_config,
    enable_dca_v2,
    disable_dca_v2,
    get_dca_v2_status,
    get_dca_v2_spending,
    get_dca_v2_crash_reserve,
    get_dca_v2_auto_config,
    simulate_dca_v2,
)

st.set_page_config(page_title="DCA Config – InvestX", page_icon="⚙️", layout="wide")
st.title("⚙️ Configuration DCA")

token = require_auth()
if not token:
    st.stop()

# ── Sélection du mode ──
mode = st.radio(
    "Mode DCA",
    ["simple (v1)", "RSI avancé (v2)"],
    horizontal=True,
    help="v1 = montant fixe quotidien · v2 = montant dynamique RSI × MVRV × MA200",
)


# ══════════════════════════════════════════════════════
# v1 – DCA simple
# ══════════════════════════════════════════════════════
if mode == "simple (v1)":
    st.subheader("DCA Simple")

    current = None
    try:
        current = get_dca_config(token)
    except Exception as e:
        st.warning(f"Impossible de charger la config : {e}")

    with st.form("dca_v1_form"):
        enabled = st.checkbox(
            "DCA activé",
            value=current.get("enabled", False) if current else False,
        )
        symbol = st.selectbox(
            "Paire",
            ["BTCEUR", "ETHEUR", "BTCUSDT", "ETHUSDT"],
            index=(
                ["BTCEUR", "ETHEUR", "BTCUSDT", "ETHUSDT"].index(
                    current.get("symbol", "BTCEUR")
                )
                if current and current.get("symbol") in ["BTCEUR", "ETHEUR", "BTCUSDT", "ETHUSDT"]
                else 0
            ),
        )
        daily_amount = st.number_input(
            "Montant quotidien (€)",
            min_value=5.0, max_value=10000.0, step=1.0,
            value=max(5.0, current.get("daily_amount_eur", 10.0)) if current else 10.0,
            help="Minimum 5 € (exigé par Binance)",
        )
        col1, col2 = st.columns(2)
        with col1:
            hour = st.number_input(
                "Heure", min_value=0, max_value=23,
                value=current.get("execution_hour", 10) if current else 10,
            )
        with col2:
            minute = st.number_input(
                "Minute", min_value=0, max_value=59,
                value=current.get("execution_minute", 0) if current else 0,
            )

        submitted = st.form_submit_button("💾 Sauvegarder")

    if submitted:
        payload = {
            "enabled": enabled,
            "symbol": symbol,
            "daily_amount_eur": daily_amount,
            "execution_hour": hour,
            "execution_minute": minute,
            "timezone": "Europe/Paris",
            "mode": "simple",
        }
        try:
            update_dca_config(token, payload)
            st.success("✅ Config DCA v1 sauvegardée !")
        except Exception as e:
            st.error(f"❌ Erreur : {e}")

    st.stop()


# ══════════════════════════════════════════════════════
# v2 – DCA RSI avancé
# ══════════════════════════════════════════════════════
st.subheader("DCA RSI v2 – Stratégie avancée")
st.caption(
    "Le montant journalier de base pilote automatiquement tous les paramètres. "
    "Vous pouvez modifier chaque valeur manuellement."
)

# Charger la config v2 existante
v2_config = None
try:
    v2_config = get_dca_v2_config(token)
except Exception as e:
    st.warning(f"Impossible de charger la config v2 : {e}")


# ────────────────────────────────────────────────────
# ÉTAPE 1 : Montant de base + auto-calcul
# ────────────────────────────────────────────────────
st.markdown("### 💰 Montant de base quotidien")

base_amount = st.slider(
    "Montant de base (×1) en $",
    min_value=5.0,
    max_value=500.0,
    value=max(5.0, float((v2_config or {}).get("base_daily_amount", 12.0))),
    step=1.0,
    help="Minimum 5 $ (exigé par Binance). C'est le montant investi quand RSI = WARM (×1) et MVRV = FAIR (×1).",
)

# Auto-calcul des paramètres recommandés
auto_params = None
try:
    auto_params = get_dca_v2_auto_config(base_amount)
except Exception:
    # Calcul local en fallback
    auto_params = {
        "spending_caps": {
            "daily_cap": round(base_amount * 12.5, 2),
            "weekly_cap": round(base_amount * 33.3, 2),
            "monthly_cap": round(base_amount * 125, 2),
        },
        "boost": {
            "threshold": round(base_amount * 10, 2),
            "cooldown_hours": 24,
        },
        "crash_reserve_budget": round(base_amount * 91.7, 2),
    }

auto_caps = auto_params.get("spending_caps", {})
auto_boost = auto_params.get("boost", {})
auto_crash_budget = auto_params.get("crash_reserve_budget", 1100.0)


# ────────────────────────────────────────────────────
# ÉTAPE 2 : Simulation – « Combien j'investis selon le marché ? »
# ────────────────────────────────────────────────────
st.markdown("### 📊 Simulation : montants selon les conditions de marché")
st.caption(
    "Ce tableau montre combien sera investi pour chaque combinaison RSI × MVRV, "
    "en régime Normal (90% BTC / 10% ETH)."
)

# Lancer la simulation
sim_data = None
try:
    sim_data = simulate_dca_v2({"base_daily_amount": base_amount})
except Exception as e:
    st.info(f"Simulation indisponible : {e}")

if sim_data:
    scenarios = sim_data.get("scenarios", [])
    extremes = sim_data.get("extremes", {})

    # Afficher les extrêmes en métriques
    if extremes:
        c1, c2, c3 = st.columns(3)
        c1.metric("Min / jour", f"${extremes.get('min_daily', 0):.2f}")
        c2.metric("Max / jour", f"${extremes.get('max_daily', 0):.2f}")
        c3.metric("Moy / jour", f"${extremes.get('avg_daily', 0):.2f}")

        c4, c5, c6 = st.columns(3)
        c4.metric("Est. min / mois", f"${extremes.get('est_monthly_min', 0):.0f}")
        c5.metric("Est. max / mois", f"${extremes.get('est_monthly_max', 0):.0f}")
        c6.metric("Est. moy / mois", f"${extremes.get('est_monthly_avg', 0):.0f}")

    # Construire la grille pivot : RSI (lignes) × MVRV (colonnes) pour régime NORMAL
    normal_rows = [
        s for s in scenarios if s.get("regime") == "NORMAL"
    ]
    if normal_rows:
        df = pd.DataFrame(normal_rows)
        pivot = df.pivot_table(
            index="rsi_bracket",
            columns="mvrv_label",
            values="total_amount",
            aggfunc="first",
        )
        # Ordonner les colonnes et lignes
        col_order = ["DEEP_UNDERVALUED", "MODERATE_UNDERVALUED", "FAIR_OR_ABOVE"]
        row_order = ["OVERSOLD", "NEUTRAL", "WARM", "OVERBOUGHT"]
        pivot = pivot.reindex(
            index=[r for r in row_order if r in pivot.index],
            columns=[c for c in col_order if c in pivot.columns],
        )
        # Renommer pour l'affichage
        col_labels = {
            "DEEP_UNDERVALUED": "🔥 MVRV < 0.85 (×2)",
            "MODERATE_UNDERVALUED": "📈 MVRV < 1.0 (×1.5)",
            "FAIR_OR_ABOVE": "➡️ MVRV ≥ 1.0 (×1)",
        }
        row_labels = {
            "OVERSOLD": f"🟢 OVERSOLD (×3) = ${base_amount * 3:.0f} base",
            "NEUTRAL": f"🔵 NEUTRAL (×2) = ${base_amount * 2:.0f} base",
            "WARM": f"🟡 WARM (×1) = ${base_amount:.0f} base",
            "OVERBOUGHT": "🔴 OVERBOUGHT (×0) = $0",
        }
        pivot = pivot.rename(index=row_labels, columns=col_labels)

        st.dataframe(
            pivot.style.format("${:.2f}").applymap(
                lambda v: (
                    "background-color: #1a472a; color: #4ade80"
                    if isinstance(v, (int, float)) and v >= base_amount * 3
                    else (
                        "background-color: #172554; color: #60a5fa"
                        if isinstance(v, (int, float)) and v >= base_amount
                        else (
                            "background-color: #451a03; color: #fbbf24"
                            if isinstance(v, (int, float)) and v > 0
                            else "background-color: #7f1d1d; color: #f87171"
                        )
                    )
                )
            ),
            use_container_width=True,
        )

        st.info(
            f"💡 **Avec un base de ${base_amount:.0f}/jour** :\n"
            f"- En accumulation forte (RSI OVERSOLD + MVRV < 0.85) → **${base_amount * 3 * 2:.0f}/jour**\n"
            f"- En marché neutre (RSI NEUTRAL + MVRV fair) → **${base_amount * 2:.0f}/jour**\n"
            f"- En surchauffe (RSI OVERBOUGHT) → **$0/jour** (aucun achat)"
        )


# ────────────────────────────────────────────────────
# ÉTAPE 3 : Configuration détaillée (override manuel)
# ────────────────────────────────────────────────────
st.markdown("### ⚙️ Paramètres détaillés")

manual_override = st.toggle(
    "✏️ Mode avancé : modifier manuellement les paramètres",
    value=False,
    help="Par défaut, les paramètres sont calculés automatiquement. Activez pour les ajuster.",
)

# Valeurs existantes dans la config (ou auto si première fois)
existing_caps = (v2_config or {}).get("spending_caps", {})
existing_boost = (v2_config or {}).get("boost", {})
existing_crash = (v2_config or {}).get("crash_reserve", {})

with st.form("dca_v2_form"):
    # ── Activation + Devise + Horaire ──
    col_en, col_q = st.columns(2)
    with col_en:
        enabled = st.checkbox(
            "DCA v2 activé",
            value=(v2_config or {}).get("enabled", False),
        )
    with col_q:
        quote = st.selectbox(
            "Devise",
            ["EUR", "USD"],
            index=["EUR", "USD"].index((v2_config or {}).get("quote_currency", "EUR")),
        )

    col_h, col_m = st.columns(2)
    with col_h:
        hour = st.number_input(
            "Heure d'exécution (UTC)", min_value=0, max_value=23,
            value=(v2_config or {}).get("execution_hour", 10),
        )
    with col_m:
        minute = st.number_input(
            "Minute", min_value=0, max_value=59,
            value=(v2_config or {}).get("execution_minute", 0),
        )

    # ── MVRV ──
    mvrv_on = st.checkbox(
        "Multiplicateur MVRV activé",
        value=(v2_config or {}).get("mvrv_enabled", True),
    )

    st.divider()

    # ── Spending Caps ──
    st.markdown("#### 🛡️ Spending Caps (plafonds de dépenses)")
    if not manual_override:
        st.caption(
            f"Calculés automatiquement pour un base de ${base_amount:.0f}/jour. "
            "Activez le mode avancé pour modifier."
        )

    col_d, col_w, col_mo = st.columns(3)
    with col_d:
        daily_cap = st.number_input(
            "Cap quotidien ($)",
            min_value=1.0, step=10.0,
            value=float(
                existing_caps.get("daily_cap", auto_caps.get("daily_cap", 150.0))
                if manual_override
                else auto_caps.get("daily_cap", 150.0)
            ),
            disabled=not manual_override,
        )
    with col_w:
        weekly_cap = st.number_input(
            "Cap hebdomadaire ($)",
            min_value=1.0, step=50.0,
            value=float(
                existing_caps.get("weekly_cap", auto_caps.get("weekly_cap", 400.0))
                if manual_override
                else auto_caps.get("weekly_cap", 400.0)
            ),
            disabled=not manual_override,
        )
    with col_mo:
        monthly_cap = st.number_input(
            "Cap mensuel ($)",
            min_value=1.0, step=100.0,
            value=float(
                existing_caps.get("monthly_cap", auto_caps.get("monthly_cap", 1500.0))
                if manual_override
                else auto_caps.get("monthly_cap", 1500.0)
            ),
            disabled=not manual_override,
        )

    st.divider()

    # ── Boost Cooldown ──
    st.markdown("#### ⏱️ Boost Cooldown")
    st.caption(
        "Quand le montant dépasse le seuil, un délai est imposé avant le prochain boost."
    )

    col_bt, col_bh = st.columns(2)
    with col_bt:
        boost_threshold = st.number_input(
            "Seuil boost ($)",
            min_value=1.0, step=10.0,
            value=float(
                existing_boost.get("threshold", auto_boost.get("threshold", 120.0))
                if manual_override
                else auto_boost.get("threshold", 120.0)
            ),
            disabled=not manual_override,
        )
    with col_bh:
        boost_cooldown = st.number_input(
            "Cooldown (heures)",
            min_value=0, max_value=168, step=1,
            value=int(
                existing_boost.get("cooldown_hours", auto_boost.get("cooldown_hours", 24))
                if manual_override
                else auto_boost.get("cooldown_hours", 24)
            ),
            disabled=not manual_override,
        )

    st.divider()

    # ── Crash Reserve ──
    st.markdown("#### 🚨 Crash Reserve")
    st.caption(
        "Réserve débloquée automatiquement lors de chutes brutales "
        "(-15%, -25%, -35% depuis le plus haut)."
    )

    crash_on = st.checkbox(
        "Crash Reserve activée",
        value=existing_crash.get("enabled", True),
    )
    crash_budget = st.number_input(
        "Budget total Crash Reserve ($)",
        min_value=0.0, step=100.0,
        value=float(
            existing_crash.get("total_budget", auto_crash_budget)
            if manual_override
            else auto_crash_budget
        ),
        disabled=not manual_override,
    )

    submitted = st.form_submit_button("💾 Sauvegarder la configuration v2")


# ── Sauvegarde ──
if submitted:
    final_caps = {
        "daily_cap": daily_cap if manual_override else auto_caps.get("daily_cap", 150.0),
        "weekly_cap": weekly_cap if manual_override else auto_caps.get("weekly_cap", 400.0),
        "monthly_cap": monthly_cap if manual_override else auto_caps.get("monthly_cap", 1500.0),
    }
    final_boost = {
        "threshold": boost_threshold if manual_override else auto_boost.get("threshold", 120.0),
        "cooldown_hours": boost_cooldown if manual_override else auto_boost.get("cooldown_hours", 24),
    }
    final_crash_budget = (
        crash_budget if manual_override else auto_crash_budget
    )

    payload = {
        "enabled": enabled,
        "quote_currency": quote,
        "base_daily_amount": base_amount,
        "execution_hour": hour,
        "execution_minute": minute,
        "timezone": "UTC",
        "mvrv_enabled": mvrv_on,
        "spending_caps": final_caps,
        "boost": final_boost,
        "crash_reserve": {
            "enabled": crash_on,
            "total_budget": final_crash_budget,
        },
    }
    try:
        update_dca_v2_config(token, payload)
        if enabled:
            enable_dca_v2(token)
        else:
            disable_dca_v2(token)
        st.success("✅ Configuration DCA RSI v2 sauvegardée !")
        st.rerun()
    except Exception as e:
        st.error(f"❌ Erreur : {e}")


# ────────────────────────────────────────────────────
# ÉTAPE 4 : Indicateurs temps réel + Spending + Crash
# ────────────────────────────────────────────────────
st.divider()
st.markdown("### 📡 État actuel")

# ── Indicateurs en temps réel ──
with st.expander("📊 Indicateurs en temps réel", expanded=True):
    try:
        status = get_dca_v2_status(token)
        if "error" in status:
            st.warning(status["error"])
        else:
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("RSI (14j)", f"{status.get('rsi', 0):.1f}", status.get("rsi_bracket", ""))
            c2.metric("MA200", f"${status.get('ma200', 0):,.0f}", status.get("regime", ""))
            mvrv_val = status.get("mvrv")
            c3.metric("MVRV", f"{mvrv_val:.2f}" if mvrv_val else "N/A")
            c4.metric("Montant prévu", f"${status.get('raw_amount', 0):.2f}")

            st.divider()
            col_a, col_b = st.columns(2)
            with col_a:
                st.write("**Split calculé**")
                st.write(f"BTC ({status.get('btc_pct', 90)}%) : ${status.get('btc_amount', 0):.2f}")
                st.write(f"ETH ({status.get('eth_pct', 10)}%) : ${status.get('eth_amount', 0):.2f}")
            with col_b:
                if status.get("crash_reserve"):
                    cr = status["crash_reserve"]
                    st.write("**Crash Reserve**")
                    st.write(f"Drop: {cr.get('drop_pct', 0):.1f}%")
                    st.write(f"Niveaux déclenchés: {cr.get('triggered_levels', [])}")
                    st.write(f"Budget restant: ${cr.get('reserve_remaining', 0):.2f}")
    except Exception as e:
        st.info(f"Indicateurs indisponibles : {e}")

# ── Spending ──
with st.expander("💰 Dépenses en cours"):
    try:
        spending = get_dca_v2_spending(token)
        c1, c2, c3 = st.columns(3)
        c1.metric(
            "Aujourd'hui",
            f"${spending.get('spent_today', 0):.2f}",
            f"reste ${spending.get('daily_remaining', 0):.2f}",
        )
        c2.metric(
            "Cette semaine",
            f"${spending.get('spent_this_week', 0):.2f}",
            f"reste ${spending.get('weekly_remaining', 0):.2f}",
        )
        c3.metric(
            "Ce mois",
            f"${spending.get('spent_this_month', 0):.2f}",
            f"reste ${spending.get('monthly_remaining', 0):.2f}",
        )
    except Exception as e:
        st.info(f"Dépenses indisponibles : {e}")

# ── Crash Reserve ──
with st.expander("🚨 Crash Reserve"):
    try:
        reserve = get_dca_v2_crash_reserve(token)
        c1, c2, c3 = st.columns(3)
        c1.metric("Budget total", f"${reserve.get('total_budget', 0):.2f}")
        c2.metric("Dépensé", f"${reserve.get('spent', 0):.2f}")
        c3.metric("Restant", f"${reserve.get('remaining', 0):.2f}")
        if reserve.get("levels_triggered"):
            st.write(f"Niveaux déclenchés : {', '.join(reserve['levels_triggered'])}")
    except Exception as e:
        st.info(f"Crash reserve indisponible : {e}")
