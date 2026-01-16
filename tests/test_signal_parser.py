"""Tests for signal_parser module."""

from datetime import datetime

import pytest

from src.signal_parser import Signal, SignalAction, SignalParser


class TestSignalParser:
    """Test cases for SignalParser."""

    def setup_method(self) -> None:
        """Set up test fixtures."""
        self.parser = SignalParser(valid_symbols=["XAUUSD", "BTCUSD", "ETHUSD"])

    def test_parse_buy_signal(self) -> None:
        """Test parsing BUY signal with Ark_BTC prefix."""
        message = "Ark_BTC Alert: BUY XAUUSD SL:1920.50 TP:1950.00"
        signal = self.parser.parse(message)

        assert signal is not None
        assert signal.action == SignalAction.BUY
        assert signal.symbol == "XAUUSD"
        assert signal.stop_loss == 1920.50
        assert signal.take_profit == 1950.00
        assert not signal.is_close_signal()

    def test_parse_sell_signal(self) -> None:
        """Test parsing SELL signal with Ark_BTC prefix."""
        message = "Ark_BTC Indicator SELL BTCUSD SL:45000.00 TP:42000.00"
        signal = self.parser.parse(message)

        assert signal is not None
        assert signal.action == SignalAction.SELL
        assert signal.symbol == "BTCUSD"
        assert signal.stop_loss == 45000.00
        assert signal.take_profit == 42000.00
        assert not signal.is_close_signal()

    def test_parse_lowercase_action(self) -> None:
        """Test parsing with lowercase action."""
        message = "Ark_BTC buy XAUUSD SL:1920.50 TP:1950.00"
        signal = self.parser.parse(message)

        assert signal is not None
        assert signal.action == SignalAction.BUY

    def test_parse_invalid_symbol(self) -> None:
        """Test parsing with invalid symbol."""
        message = "Ark_BTC BUY INVALID SL:100.00 TP:110.00"
        signal = self.parser.parse(message)

        assert signal is None

    def test_parse_without_ark_prefix(self) -> None:
        """Test parsing without Ark_BTC prefix returns None."""
        message = "BUY XAUUSD SL:1920.50 TP:1950.00"
        signal = self.parser.parse(message)

        assert signal is None

    def test_parse_invalid_format(self) -> None:
        """Test parsing with invalid format."""
        invalid_messages = [
            "XAUUSD BUY",
            "BUY XAUUSD",
            "Ark_BTC BUY XAUUSD",
            "Ark_BTC BUY XAUUSD SL:1920.50",
            "Random text message",
            "",
            "   ",
        ]

        for message in invalid_messages:
            signal = self.parser.parse(message)
            assert signal is None, f"Expected None for: {message}"

    def test_parse_with_whitespace(self) -> None:
        """Test parsing with leading/trailing whitespace."""
        message = "  Ark_BTC BUY XAUUSD SL:1920.50 TP:1950.00  "
        signal = self.parser.parse(message)

        assert signal is not None
        assert signal.action == SignalAction.BUY

    def test_is_valid_signal(self) -> None:
        """Test is_valid_signal method."""
        assert self.parser.is_valid_signal("Ark_BTC BUY XAUUSD SL:1920.50 TP:1950.00")
        assert not self.parser.is_valid_signal("BUY XAUUSD SL:1920.50 TP:1950.00")
        assert not self.parser.is_valid_signal("Invalid message")

    def test_parse_all_symbols(self) -> None:
        """Test parsing signals for all valid symbols."""
        symbols = ["XAUUSD", "BTCUSD", "ETHUSD"]

        for symbol in symbols:
            message = f"Ark_BTC BUY {symbol} SL:100.00 TP:110.00"
            signal = self.parser.parse(message)
            assert signal is not None
            assert signal.symbol == symbol

    def test_parser_without_symbol_filter(self) -> None:
        """Test parser without symbol filter accepts any symbol."""
        parser = SignalParser()  # No valid_symbols filter
        message = "Ark_BTC BUY ANYSYMBOL SL:100.00 TP:110.00"
        signal = parser.parse(message)

        assert signal is not None
        assert signal.symbol == "ANYSYMBOL"


class TestCloseSignalParser:
    """Test cases for close signal parsing."""

    def setup_method(self) -> None:
        """Set up test fixtures."""
        self.parser = SignalParser(valid_symbols=["XAUUSD", "BTCUSD", "ETHUSD"])

    def test_parse_close_long_signal(self) -> None:
        """Test parsing close long signal."""
        message = "ロング決済サイン at price: 2650.50"
        signal = self.parser.parse(message)

        assert signal is not None
        assert signal.action == SignalAction.CLOSE_LONG
        assert signal.close_price == 2650.50
        assert signal.is_close_signal()
        assert signal.stop_loss is None
        assert signal.take_profit is None

    def test_parse_close_short_signal(self) -> None:
        """Test parsing close short signal."""
        message = "ショート決済サイン at price: 2600.00"
        signal = self.parser.parse(message)

        assert signal is not None
        assert signal.action == SignalAction.CLOSE_SHORT
        assert signal.close_price == 2600.00
        assert signal.is_close_signal()

    def test_close_signal_uses_first_symbol(self) -> None:
        """Test that close signal uses first valid symbol."""
        message = "ロング決済サイン at price: 2650.50"
        signal = self.parser.parse(message)

        assert signal is not None
        assert signal.symbol == "XAUUSD"  # First in valid_symbols list

    def test_close_signal_default_symbol(self) -> None:
        """Test close signal with no valid_symbols uses XAUUSD."""
        parser = SignalParser()  # No valid_symbols
        message = "ロング決済サイン at price: 2650.50"
        signal = parser.parse(message)

        assert signal is not None
        assert signal.symbol == "XAUUSD"

    def test_close_signal_with_whitespace(self) -> None:
        """Test close signal with extra whitespace."""
        message = "  ロング決済サイン at price:  2650.50  "
        signal = self.parser.parse(message)

        assert signal is not None
        assert signal.action == SignalAction.CLOSE_LONG

    def test_invalid_close_signal_format(self) -> None:
        """Test invalid close signal formats."""
        invalid_messages = [
            "ロング決済サイン price: 2650.50",  # Missing "at"
            "ロング決済サイン at price:",  # Missing price
            "決済サイン at price: 2650.50",  # Missing direction
        ]

        for message in invalid_messages:
            signal = self.parser.parse(message)
            assert signal is None, f"Expected None for: {message}"


class TestSignal:
    """Test cases for Signal dataclass."""

    def test_entry_signal_str(self) -> None:
        """Test entry Signal string representation."""
        signal = Signal(
            action=SignalAction.BUY,
            symbol="XAUUSD",
            stop_loss=1920.50,
            take_profit=1950.00,
            timestamp=datetime.now(),
        )

        result = str(signal)
        assert "ロングエントリーサイン" in result
        assert "XAUUSD" in result
        assert "SL:1920.5" in result
        assert "TP:1950.0" in result

    def test_close_signal_str(self) -> None:
        """Test close Signal string representation."""
        signal = Signal(
            action=SignalAction.CLOSE_LONG,
            symbol="XAUUSD",
            close_price=2650.50,
            timestamp=datetime.now(),
        )

        result = str(signal)
        assert "ロング決済サイン" in result
        assert "XAUUSD" in result
        assert "at price: 2650.5" in result

    def test_is_close_signal(self) -> None:
        """Test is_close_signal method."""
        entry_signal = Signal(
            action=SignalAction.BUY,
            symbol="XAUUSD",
            stop_loss=1920.50,
            take_profit=1950.00,
            timestamp=datetime.now(),
        )
        assert not entry_signal.is_close_signal()

        close_signal = Signal(
            action=SignalAction.CLOSE_LONG,
            symbol="XAUUSD",
            close_price=2650.50,
            timestamp=datetime.now(),
        )
        assert close_signal.is_close_signal()

        close_short = Signal(
            action=SignalAction.CLOSE_SHORT,
            symbol="XAUUSD",
            close_price=2650.50,
            timestamp=datetime.now(),
        )
        assert close_short.is_close_signal()
