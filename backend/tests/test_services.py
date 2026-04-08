"""
Tests unitaires pour les services critiques InvestX.
"""

from __future__ import annotations

import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime, timezone


# ══════════════════════════════════════════════════════
# Tests market_data_service
# ══════════════════════════════════════════════════════

class TestMarketDataCache:
    """Teste le cache TTL de market_data_service."""

    def test_cache_set_and_get(self):
        from app.services.market_data_service import _cache_set, _cache_get, _cache
        _cache.clear()
        _cache_set("test_key", 42, ttl_seconds=60)
        assert _cache_get("test_key") == 42

    def test_cache_expired(self):
        from app.services.market_data_service import _cache_set, _cache_get, _cache
        _cache.clear()
        _cache_set("expired_key", 42, ttl_seconds=-1)
        assert _cache_get("expired_key") is None

    def test_cache_miss(self):
        from app.services.market_data_service import _cache_get, _cache
        _cache.clear()
        assert _cache_get("nonexistent") is None


class TestRSIComputation:
    """Teste le calcul RSI de market_data_service."""

    def test_compute_rsi_with_valid_data(self):
        from app.services.market_data_service import compute_rsi
        # Créer une série de prix monotone croissante → RSI proche de 100
        closes = [float(i) for i in range(1, 20)]
        rsi = compute_rsi(closes, period=14)
        assert rsi is not None
        assert 80 < rsi <= 100

    def test_compute_rsi_with_declining_data(self):
        from app.services.market_data_service import compute_rsi
        # Série décroissante → RSI proche de 0
        closes = [float(100 - i) for i in range(20)]
        rsi = compute_rsi(closes, period=14)
        assert rsi is not None
        assert 0 <= rsi < 20

    def test_compute_rsi_insufficient_data(self):
        from app.services.market_data_service import compute_rsi
        with pytest.raises(ValueError):
            compute_rsi([1.0, 2.0, 3.0], period=14)


class TestRollingHigh:
    """Teste le calcul du rolling high."""

    def test_rolling_high_basic(self):
        from app.services.market_data_service import compute_rolling_high
        closes = list(range(200))
        rh = compute_rolling_high(closes)
        assert rh == 199

    def test_rolling_high_short_data(self):
        from app.services.market_data_service import compute_rolling_high
        closes = [10, 20, 30]
        rh = compute_rolling_high(closes)
        assert rh == 30

    def test_rolling_high_empty(self):
        from app.services.market_data_service import compute_rolling_high
        assert compute_rolling_high([]) == 0.0


class TestDropPct:
    """Teste le calcul du pourcentage de baisse."""

    def test_drop_pct(self):
        from app.services.market_data_service import compute_drop_pct
        assert compute_drop_pct(80, 100) == -20.0

    def test_drop_pct_zero_high(self):
        from app.services.market_data_service import compute_drop_pct
        assert compute_drop_pct(80, 0) == 0.0

    def test_no_drop(self):
        from app.services.market_data_service import compute_drop_pct
        assert compute_drop_pct(100, 100) == 0.0


class TestCrashLevels:
    """Teste la détection des niveaux de crash."""

    def test_crash_level_triggered(self):
        from app.services.market_data_service import get_crash_levels_triggered
        from app.core.constants import DEFAULT_CRASH_LEVELS
        triggered = get_crash_levels_triggered(-20.0, DEFAULT_CRASH_LEVELS)
        assert "LEVEL_15" in triggered

    def test_no_crash_level(self):
        from app.services.market_data_service import get_crash_levels_triggered
        from app.core.constants import DEFAULT_CRASH_LEVELS
        triggered = get_crash_levels_triggered(-5.0, DEFAULT_CRASH_LEVELS)
        assert len(triggered) == 0


# ══════════════════════════════════════════════════════
# Tests utils
# ══════════════════════════════════════════════════════

class TestMoneyUtils:
    """Teste les utilitaires monétaires."""

    def test_round_eur(self):
        from app.utils.money_utils import round_eur
        assert round_eur(12.3456789) == 12.35

    def test_round_eur_large(self):
        from app.utils.money_utils import round_eur
        assert round_eur(0.005) == 0.01


class TestValidators:
    """Teste les validateurs."""

    def test_valid_symbol(self):
        from app.utils.validators import is_valid_symbol
        assert is_valid_symbol("BTCUSDC") is True

    def test_invalid_symbol(self):
        from app.utils.validators import is_valid_symbol
        assert is_valid_symbol("INVALIDXYZ") is False


class TestDatetimeUtils:
    """Teste les utilitaires de dates."""

    def test_now_paris(self):
        from app.utils.datetime_utils import now_paris
        result = now_paris()
        assert isinstance(result, datetime)

    def test_utc_now(self):
        from app.utils.datetime_utils import utc_now
        result = utc_now()
        assert isinstance(result, datetime)


# ══════════════════════════════════════════════════════
# Tests DCA service (fonctions pures)
# ══════════════════════════════════════════════════════

class TestDCABacktest:
    """Teste le backtesting (fonction pure, pas d'appel externe)."""

    @patch("app.services.dca_service.httpx.get")
    def test_backtest_returns_structure(self, mock_get):
        """Teste que le backtesting retourne la bonne structure."""
        # Simuler des klines Binance
        import time
        now = int(time.time() * 1000)
        klines = []
        for i in range(30):
            ts = now - (30 - i) * 86400000
            price = 60000 + i * 100
            klines.append([ts, price, price + 50, price - 50, price, 1000, ts + 86400000])

        mock_response = MagicMock()
        mock_response.json.return_value = klines
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response

        from app.services.dca_service import backtest_rsi_v2
        result = backtest_rsi_v2(12.0, 30, "BTCUSDC")

        assert "daily_data" in result
        assert "summary" in result
        assert len(result["daily_data"]) == 30


class TestDCASimulation:
    """Teste la simulation de scénarios (fonction pure)."""

    def test_simulate_scenarios_basic(self):
        from app.services.dca_service import simulate_scenarios
        result = simulate_scenarios(12.0)
        assert "scenarios" in result
        assert "extremes" in result
        assert len(result["scenarios"]) > 0

    def test_simulate_scenarios_zero_amount(self):
        from app.services.dca_service import simulate_scenarios
        result = simulate_scenarios(0.0)
        assert "scenarios" in result
        # Tous les montants doivent être 0
        for s in result["scenarios"]:
            assert s["total_amount"] == 0


# ══════════════════════════════════════════════════════
# Tests constants
# ══════════════════════════════════════════════════════

class TestConstants:
    """Vérifie la cohérence des constantes."""

    def test_allowed_symbols_not_empty(self):
        from app.core.constants import ALLOWED_SYMBOLS
        assert len(ALLOWED_SYMBOLS) > 0

    def test_exchange_symbols_exist(self):
        from app.core.constants import EXCHANGE_SYMBOLS
        assert "binance" in EXCHANGE_SYMBOLS
        assert "revolutx" in EXCHANGE_SYMBOLS

    def test_rsi_brackets_ordered(self):
        from app.core.constants import DEFAULT_RSI_BRACKETS
        max_rsis = [b["max_rsi"] for b in DEFAULT_RSI_BRACKETS]
        assert max_rsis == sorted(max_rsis)

    def test_mvrv_thresholds_have_multiplier(self):
        from app.core.constants import DEFAULT_MVRV_THRESHOLDS
        for t in DEFAULT_MVRV_THRESHOLDS:
            assert "multiplier" in t
            assert t["multiplier"] > 0
