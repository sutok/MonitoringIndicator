"""Tests for order_executor module."""

import json
import tempfile
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from src.config import Config, SymbolConfig, TradeControlConfig
from src.order_executor import DuplicateChecker, OrderExecutor, TradingTimeChecker
from src.signal_parser import Signal, SignalAction


class TestDuplicateChecker:
    """Test cases for DuplicateChecker."""

    def test_first_signal_not_duplicate(self) -> None:
        """Test that first signal is not a duplicate."""
        checker = DuplicateChecker(threshold_seconds=180)
        signal = Signal(
            action=SignalAction.BUY,
            symbol="XAUUSD",
            stop_loss=1920.0,
            take_profit=1950.0,
            timestamp=datetime.now(),
        )

        assert checker.is_duplicate(signal) is False

    def test_same_signal_within_threshold_is_duplicate(self) -> None:
        """Test that same signal within threshold is duplicate."""
        checker = DuplicateChecker(threshold_seconds=180)
        signal = Signal(
            action=SignalAction.BUY,
            symbol="XAUUSD",
            stop_loss=1920.0,
            take_profit=1950.0,
            timestamp=datetime.now(),
        )

        # First signal
        assert checker.is_duplicate(signal) is False
        # Same signal immediately after
        assert checker.is_duplicate(signal) is True

    def test_different_symbol_not_duplicate(self) -> None:
        """Test that different symbol is not duplicate."""
        checker = DuplicateChecker(threshold_seconds=180)

        signal1 = Signal(
            action=SignalAction.BUY,
            symbol="XAUUSD",
            stop_loss=1920.0,
            take_profit=1950.0,
            timestamp=datetime.now(),
        )
        signal2 = Signal(
            action=SignalAction.BUY,
            symbol="BTCUSD",
            stop_loss=45000.0,
            take_profit=48000.0,
            timestamp=datetime.now(),
        )

        assert checker.is_duplicate(signal1) is False
        assert checker.is_duplicate(signal2) is False

    def test_different_action_not_duplicate(self) -> None:
        """Test that different action is not duplicate."""
        checker = DuplicateChecker(threshold_seconds=180)

        signal_buy = Signal(
            action=SignalAction.BUY,
            symbol="XAUUSD",
            stop_loss=1920.0,
            take_profit=1950.0,
            timestamp=datetime.now(),
        )
        signal_sell = Signal(
            action=SignalAction.SELL,
            symbol="XAUUSD",
            stop_loss=1950.0,
            take_profit=1920.0,
            timestamp=datetime.now(),
        )

        assert checker.is_duplicate(signal_buy) is False
        assert checker.is_duplicate(signal_sell) is False

    def test_signal_after_threshold_not_duplicate(self) -> None:
        """Test that signal after threshold is not duplicate."""
        checker = DuplicateChecker(threshold_seconds=1)  # 1 second threshold

        signal = Signal(
            action=SignalAction.BUY,
            symbol="XAUUSD",
            stop_loss=1920.0,
            take_profit=1950.0,
            timestamp=datetime.now(),
        )

        # First signal
        assert checker.is_duplicate(signal) is False

        # Manually set last signal time to past using the correct key format
        key = f"XAUUSD_{SignalAction.BUY.value}"
        checker._last_signals[key] = datetime.now() - timedelta(seconds=2)

        # Should not be duplicate now
        assert checker.is_duplicate(signal) is False

    def test_clear(self) -> None:
        """Test clear method."""
        checker = DuplicateChecker(threshold_seconds=180)
        signal = Signal(
            action=SignalAction.BUY,
            symbol="XAUUSD",
            stop_loss=1920.0,
            take_profit=1950.0,
            timestamp=datetime.now(),
        )

        checker.is_duplicate(signal)
        assert len(checker._last_signals) == 1

        checker.clear()
        assert len(checker._last_signals) == 0


class TestTradingTimeChecker:
    """Test cases for TradingTimeChecker."""

    def test_can_trade_enabled_symbol(self) -> None:
        """Test can_trade with enabled symbol."""
        checker = TradingTimeChecker()
        config = SymbolConfig(enabled=True, weekend_stop=False)

        assert checker.can_trade("XAUUSD", config) is True

    def test_can_trade_disabled_symbol(self) -> None:
        """Test can_trade with disabled symbol."""
        checker = TradingTimeChecker()
        config = SymbolConfig(enabled=False)

        assert checker.can_trade("XAUUSD", config) is False

    @patch.object(TradingTimeChecker, "is_weekend", return_value=True)
    def test_can_trade_weekend_stop_on_weekend(
        self, mock_is_weekend: MagicMock
    ) -> None:
        """Test can_trade with weekend_stop on weekend."""
        checker = TradingTimeChecker()
        config = SymbolConfig(enabled=True, weekend_stop=True)

        assert checker.can_trade("XAUUSD", config) is False

    @patch.object(TradingTimeChecker, "is_weekend", return_value=False)
    def test_can_trade_weekend_stop_on_weekday(
        self, mock_is_weekend: MagicMock
    ) -> None:
        """Test can_trade with weekend_stop on weekday."""
        checker = TradingTimeChecker()
        config = SymbolConfig(enabled=True, weekend_stop=True)

        assert checker.can_trade("XAUUSD", config) is True

    @patch.object(TradingTimeChecker, "is_weekend", return_value=True)
    def test_can_trade_no_weekend_stop_on_weekend(
        self, mock_is_weekend: MagicMock
    ) -> None:
        """Test can_trade without weekend_stop on weekend."""
        checker = TradingTimeChecker()
        config = SymbolConfig(enabled=True, weekend_stop=False)

        # Should allow trading even on weekend
        assert checker.can_trade("BTCUSD", config) is True


class TestOrderExecutor:
    """Test cases for OrderExecutor."""

    def setup_method(self) -> None:
        """Set up test fixtures."""
        self.config = Config()
        self.config.mt5.login = 12345
        self.config.mt5.password = "test"
        self.config.mt5.server = "TestServer"
        self.config.symbols = {
            "XAUUSD": SymbolConfig(enabled=True, lot_size=0.01, weekend_stop=True),
            "BTCUSD": SymbolConfig(enabled=True, lot_size=0.02, weekend_stop=False),
        }
        self.config.trading.duplicate_threshold_seconds = 180

    def test_init(self) -> None:
        """Test OrderExecutor initialization."""
        executor = OrderExecutor(self.config)

        assert executor.config == self.config
        assert isinstance(executor.duplicate_checker, DuplicateChecker)
        assert isinstance(executor.time_checker, TradingTimeChecker)
        assert executor._connected is False

    def test_is_connected_default(self) -> None:
        """Test is_connected returns False by default."""
        executor = OrderExecutor(self.config)
        assert executor.is_connected() is False

    def test_execute_duplicate_signal(self) -> None:
        """Test execute with duplicate signal."""
        executor = OrderExecutor(self.config)
        executor._connected = True

        signal = Signal(
            action=SignalAction.BUY,
            symbol="XAUUSD",
            stop_loss=1920.0,
            take_profit=1950.0,
            timestamp=datetime.now(),
        )

        # First execution - mark as seen
        executor.duplicate_checker.is_duplicate(signal)

        # Second execution - should be rejected as duplicate
        result = executor.execute(signal)
        assert result.success is False
        assert "Duplicate" in (result.error_message or "")

    def test_execute_unknown_symbol(self) -> None:
        """Test execute with unknown symbol."""
        executor = OrderExecutor(self.config)
        executor._connected = True

        signal = Signal(
            action=SignalAction.BUY,
            symbol="UNKNOWN",
            stop_loss=100.0,
            take_profit=110.0,
            timestamp=datetime.now(),
        )

        result = executor.execute(signal)
        assert result.success is False
        assert "Unknown symbol" in (result.error_message or "")

    @patch.object(TradingTimeChecker, "is_weekend", return_value=False)
    def test_execute_not_connected(self, mock_is_weekend: MagicMock) -> None:
        """Test execute when not connected."""
        executor = OrderExecutor(self.config)
        # Not connected

        signal = Signal(
            action=SignalAction.BUY,
            symbol="XAUUSD",
            stop_loss=1920.0,
            take_profit=1950.0,
            timestamp=datetime.now(),
        )

        result = executor.execute(signal)
        assert result.success is False
        assert "Not connected" in (result.error_message or "")

    @patch.object(TradingTimeChecker, "can_trade", return_value=False)
    def test_execute_trading_not_allowed(self, mock_can_trade: MagicMock) -> None:
        """Test execute when trading is not allowed."""
        executor = OrderExecutor(self.config)
        executor._connected = True

        signal = Signal(
            action=SignalAction.BUY,
            symbol="XAUUSD",
            stop_loss=1920.0,
            take_profit=1950.0,
            timestamp=datetime.now(),
        )

        result = executor.execute(signal)
        assert result.success is False
        assert "not allowed" in (result.error_message or "")

    def test_trade_control_disabled_by_ea(self) -> None:
        """Test execute when trade is disabled by MT4 EA."""
        # Create control file with enabled=false
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump({"enabled": False}, f)
            temp_path = f.name

        try:
            self.config.trade_control = TradeControlConfig(
                enabled=True,
                control_file_path=temp_path,
                default_enabled=True,
            )
            executor = OrderExecutor(self.config)
            executor._connected = True

            signal = Signal(
                action=SignalAction.BUY,
                symbol="XAUUSD",
                stop_loss=1920.0,
                take_profit=1950.0,
                timestamp=datetime.now(),
            )

            result = executor.execute(signal)
            assert result.success is False
            assert "disabled by MT4" in (result.error_message or "")
        finally:
            Path(temp_path).unlink()

    def test_trade_control_enabled_by_ea(self) -> None:
        """Test execute when trade is enabled by MT4 EA."""
        # Create control file with enabled=true
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump({"enabled": True}, f)
            temp_path = f.name

        try:
            self.config.trade_control = TradeControlConfig(
                enabled=True,
                control_file_path=temp_path,
                default_enabled=True,
            )
            executor = OrderExecutor(self.config)
            executor._connected = True

            signal = Signal(
                action=SignalAction.BUY,
                symbol="XAUUSD",
                stop_loss=1920.0,
                take_profit=1950.0,
                timestamp=datetime.now(),
            )

            # Should pass trade control check but fail at duplicate check
            # (since we already marked this as seen in __init__)
            # Let's use a fresh signal
            executor.duplicate_checker.clear()

            result = executor.execute(signal)
            # Will fail at MT5 connection, but should not fail at trade control
            assert "disabled by MT4" not in (result.error_message or "")
        finally:
            Path(temp_path).unlink()

    def test_trade_control_not_configured(self) -> None:
        """Test execute when trade control is not configured."""
        # Default config has trade_control disabled
        executor = OrderExecutor(self.config)
        executor._connected = True

        signal = Signal(
            action=SignalAction.BUY,
            symbol="XAUUSD",
            stop_loss=1920.0,
            take_profit=1950.0,
            timestamp=datetime.now(),
        )

        # Should proceed without trade control check
        result = executor.execute(signal)
        # Will fail at duplicate or other check, not trade control
        assert "disabled by MT4" not in (result.error_message or "")
