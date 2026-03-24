# InvestX – Schéma Firestore

## Structure

```
users/{uid}
├── email: string
├── display_name: string
├── is_active: bool
├── timezone: string
├── role: string
├── created_at: timestamp
├── updated_at: timestamp
│
├── subscription/main
│   ├── provider: "stripe"
│   ├── customer_id: string
│   ├── subscription_id: string
│   ├── status: string (active|past_due|canceled|incomplete|none)
│   ├── price_id: string
│   ├── current_period_end: timestamp
│   ├── cancel_at_period_end: bool
│   ├── last_event_id: string
│   └── updated_at: timestamp
│
├── dca_config/main
│   ├── enabled: bool
│   ├── symbol: string (BTCEUR|ETHEUR|BNBEUR|ADAEUR|SOLEUR)
│   ├── daily_amount_eur: float
│   ├── execution_hour: int (0-23)
│   ├── execution_minute: int (0-59)
│   ├── timezone: string
│   ├── mode: "simple"
│   ├── created_at: timestamp
│   └── updated_at: timestamp
│
├── binance_account/main
│   ├── exchange: "binance"
│   ├── secret_ref: string (chemin Secret Manager)
│   ├── label: string
│   ├── is_connected: bool
│   ├── permissions_validated: bool
│   ├── last_validation_at: timestamp
│   ├── created_at: timestamp
│   └── updated_at: timestamp
│
├── telegram/main
│   ├── enabled: bool
│   ├── chat_id: string
│   ├── username: string
│   ├── notify_orders: bool
│   ├── notify_errors: bool
│   ├── notify_subscription: bool
│   ├── linked_at: timestamp
│   └── updated_at: timestamp
│
├── orders/{order_id}
│   ├── symbol: string
│   ├── side: "BUY"
│   ├── amount_eur: float
│   ├── quantity: float
│   ├── price: float
│   ├── status: string (FILLED|FAILED)
│   ├── exchange_order_id: string
│   ├── executed_at: timestamp
│   ├── source: string (scheduler|manual)
│   ├── error_message: string|null
│   └── created_at: timestamp
│
├── portfolio_snapshots/{snapshot_id}
│   ├── symbol: string
│   ├── quantity_total: float
│   ├── invested_total_eur: float
│   ├── avg_buy_price: float
│   ├── market_price: float
│   ├── market_value_eur: float
│   ├── pnl_value_eur: float
│   ├── pnl_percent: float
│   └── captured_at: timestamp
│
└── audit_logs/{log_id}
    ├── action: string
    ├── status: string (SUCCESS|ERROR|INFO)
    ├── message: string
    ├── context: map
    └── created_at: timestamp

## Collections DCA RSI v2 (sous users/{uid})

```
├── dca_config/v2
│   ├── enabled: bool
│   ├── mode: "rsi_v2"
│   ├── quote_currency: string (EUR|USD)
│   ├── base_daily_amount: float
│   ├── execution_hour: int
│   ├── execution_minute: int
│   ├── timezone: string
│   ├── rsi_brackets: list[{label, min_rsi, max_rsi, multiplier}]
│   ├── mvrv_enabled: bool
│   ├── mvrv_thresholds: list[{label, max_mvrv, multiplier}]
│   ├── regime_rules: list[{label, condition, btc_pct, eth_pct}]
│   ├── spending_caps: {daily_cap, weekly_cap, monthly_cap}
│   ├── boost: {threshold, cooldown_hours}
│   ├── crash_reserve: {enabled, total_budget, levels: [{label, drop_pct, reserve_pct}]}
│   └── updated_at: timestamp
│
├── dca_spending/{period_key}     (daily_2026-03-24, weekly_2026-W13, monthly_2026-03)
│   ├── period_key: string
│   ├── amount: float
│   ├── created_at: timestamp
│   └── updated_at: timestamp
│
├── crash_reserve/main
│   ├── total_budget: float
│   ├── spent: float
│   ├── remaining: float
│   ├── levels_triggered: list[string]
│   ├── last_reset_at: timestamp
│   ├── created_at: timestamp
│   └── updated_at: timestamp
│
├── dca_boosts/last
│   ├── amount: float
│   ├── triggered_at: timestamp
│   └── updated_at: timestamp
│
└── dca_cycle_logs/{log_id}
    ├── mode: "rsi_v2"
    ├── rsi: float
    ├── rsi_bracket: string
    ├── rsi_multiplier: float
    ├── mvrv: float|null
    ├── mvrv_multiplier: float
    ├── btc_price: float
    ├── ma200: float
    ├── regime: string
    ├── btc_pct: int
    ├── eth_pct: int
    ├── btc_amount: float
    ├── eth_amount: float
    ├── crash_amount: float
    ├── total_amount: float
    ├── base_daily_amount: float
    ├── skipped: bool
    ├── skip_reason: string|null
    ├── capped: bool
    ├── cap_reason: string|null
    ├── boost_cooldown_active: bool
    ├── crash_levels_triggered: list[string]
    └── created_at: timestamp
```

dca_locks/{uid_symbol_date}
├── uid: string
├── symbol: string
├── date: string
└── locked_at: timestamp
```

## Règles de sécurité

- Chaque utilisateur ne peut accéder qu'à `users/{son_uid}` et ses sous-collections
- `dca_locks` est inaccessible côté client (backend uniquement via Admin SDK)
- Les secrets Binance ne sont JAMAIS dans Firestore (uniquement `secret_ref`)
