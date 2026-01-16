"""Tests for signal_parser module."""

import pytest

from src.signal_parser import Signal, SignalAction, SignalParser


class TestSignalParser:
    """Test cases for SignalParser."""

    def setup_method(self) -> None:
        """Set up test fixtures."""
        self.parser = SignalParser(valid_symbols=["XAUUSD", "BTCUSD", "ETHUSD"])

    def test_parse_buy_signal(self) -> None:
        """Test parsing BUY signal."""
        message = "BUY XAUUSD SL:1920.50 TP:1950.00"
        signal = self.parser.parse(message)

        assert signal is not None
        assert signal.action == SignalAction.BUY
        assert signal.symbol == "XAUUSD"
        assert signal.stop_loss == 1920.50
        assert signal.take_profit == 1950.00

    def test_parse_sell_signal(self) -> None:
        """Test parsing SELL signal."""
        message = "SELL BTCUSD SL:45000.00 TP:42000.00"
        signal = self.parser.parse(message)

        assert signal is not None
        assert signal.action == SignalAction.SELL
        assert signal.symbol == "BTCUSD"
        assert signal.stop_loss == 45000.00
        assert signal.take_profit == 42000.00

    def test_parse_lowercase_action(self) -> None:
        """Test parsing with lowercase action."""
        message = "buy XAUUSD SL:1920.50 TP:1950.00"
        signal = self.parser.parse(message)

        assert signal is not None
        assert signal.action == SignalAction.BUY

    def test_parse_invalid_symbol(self) -> None:
        """Test parsing with invalid symbol."""
        message = "BUY INVALID SL:100.00 TP:110.00"
        signal = self.parser.parse(message)

        assert signal is None

    def test_parse_invalid_format(self) -> None:
        """Test parsing with invalid format."""
        invalid_messages = [
            "XAUUSD BUY",
            "BUY XAUUSD",
            "BUY XAUUSD SL:1920.50",
            "Random text message",
            "",
            "   ",
        ]

        for message in invalid_messages:
            signal = self.parser.parse(message)
            assert signal is None, f"Expected None for: {message}"

    def test_parse_with_whitespace(self) -> None:
        """Test parsing with leading/trailing whitespace."""
        message = "  BUY XAUUSD SL:1920.50 TP:1950.00  "
        signal = self.parser.parse(message)

        assert signal is not None
        assert signal.action == SignalAction.BUY

    def test_is_valid_signal(self) -> None:
        """Test is_valid_signal method."""
        assert self.parser.is_valid_signal("BUY XAUUSD SL:1920.50 TP:1950.00")
        assert not self.parser.is_valid_signal("Invalid message")

    def test_parse_all_symbols(self) -> None:
        """Test parsing signals for all valid symbols."""
        symbols = ["XAUUSD", "BTCUSD", "ETHUSD"]

        for symbol in symbols:
            message = f"BUY {symbol} SL:100.00 TP:110.00"
            signal = self.parser.parse(message)
            assert signal is not None
            assert signal.symbol == symbol

    def test_parser_without_symbol_filter(self) -> None:
        """Test parser without symbol filter accepts any symbol."""
        parser = SignalParser()  # No valid_symbols filter
        message = "BUY ANYSYMBOL SL:100.00 TP:110.00"
        signal = parser.parse(message)

        assert signal is not None
        assert signal.symbol == "ANYSYMBOL"


class TestSignal:
    """Test cases for Signal dataclass."""

    def test_signal_str(self) -> None:
        """Test Signal string representation."""
        from datetime import datetime

        signal = Signal(
            action=SignalAction.BUY,
            symbol="XAUUSD",
            stop_loss=1920.50,
            take_profit=1950.00,
            timestamp=datetime.now(),
        )

        expected = "BUY XAUUSD SL:1920.5 TP:1950.0"
        assert str(signal) == expected
