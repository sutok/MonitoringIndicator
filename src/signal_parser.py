"""Signal parsing module for MT4 alert messages."""

import re
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Optional


class SignalAction(Enum):
    """Trading signal action type."""

    BUY = "ロングエントリーサイン"
    SELL = "ショートエントリーサイン"
    CLOSE_LONG = "ロング決済サイン"
    CLOSE_SHORT = "ショート決済サイン"


@dataclass
class Signal:
    """Parsed trading signal."""

    action: SignalAction
    symbol: str
    timestamp: datetime
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    close_price: Optional[float] = None

    def __str__(self) -> str:
        """Return string representation."""
        if self.is_close_signal():
            return f"{self.action.value} {self.symbol} at price: {self.close_price}"
        return (
            f"{self.action.value} {self.symbol} "
            f"SL:{self.stop_loss} TP:{self.take_profit}"
        )

    def is_close_signal(self) -> bool:
        """Check if this is a close signal.

        Returns:
            True if close signal, False if entry signal.
        """
        return self.action in (SignalAction.CLOSE_LONG, SignalAction.CLOSE_SHORT)


class SignalParser:
    """Parser for MT4 alert messages."""

    # Entry pattern: Ark_BTC... BUY XAUUSD SL:1920.50 TP:1950.00
    ENTRY_PATTERN = re.compile(
        r'(ショートエントリーサイン|ロングエントリーサイン)（価格:\s*([\d.]+)）.*?TP:\s*([\d.]+).*?SL:\s*([\d.]+).*?Symbol:\s*(\w+)',
        re.IGNORECASE,
    )

    # Close pattern: ロング決済サイン at price: 2650.50 or ショート決済サイン at price: 2650.50
    CLOSE_PATTERN = re.compile(
        r'(ショートエントリーサイン|ロングエントリーサイン)（価格:\s*([\d.]+)）.*?TP:\s*([\d.]+).*?SL:\s*([\d.]+).*?Symbol:\s*(\w+)',
        re.IGNORECASE,
    )

    def __init__(self, valid_symbols: Optional[list[str]] = None):
        """Initialize parser.

        Args:
            valid_symbols: List of valid symbol names. If None, all symbols accepted.
        """
        self.valid_symbols = valid_symbols

    def parse(self, message: str) -> Optional[Signal]:
        """Parse alert message into Signal.

        Args:
            message: Alert message string.

        Returns:
            Signal if message is valid, None otherwise.
        """
        message = message.strip()

        # Try entry pattern first
        entry_signal = self._parse_entry(message)
        if entry_signal:
            return entry_signal

        # Try close pattern
        close_signal = self._parse_close(message)
        if close_signal:
            return close_signal

        return None

    def _parse_entry(self, message: str) -> Optional[Signal]:
        """Parse entry signal message.

        Args:
            message: Alert message string.

        Returns:
            Signal if valid entry signal, None otherwise.
        """
        match = self.ENTRY_PATTERN.match(message)
        if not match:
            return None

        action_str, symbol, sl_str, tp_str = match.groups()

        # Validate symbol
        symbol = symbol.upper()
        if self.valid_symbols and symbol not in self.valid_symbols:
            return None

        try:
            action = (
                SignalAction.BUY if action_str.upper() == "BUY" else SignalAction.SELL
            )
            stop_loss = float(sl_str)
            take_profit = float(tp_str)
        except (ValueError, KeyError):
            return None

        return Signal(
            action=action,
            symbol=symbol,
            stop_loss=stop_loss,
            take_profit=take_profit,
            timestamp=datetime.now(),
        )

    def _parse_close(self, message: str) -> Optional[Signal]:
        """Parse close signal message.

        Args:
            message: Alert message string.

        Returns:
            Signal if valid close signal, None otherwise.
        """
        match = self.CLOSE_PATTERN.match(message)
        if not match:
            return None

        action_str, price_str = match.groups()

        try:
            if "ロング" in action_str:
                action = SignalAction.CLOSE_LONG
            else:
                action = SignalAction.CLOSE_SHORT
            close_price = float(price_str)
        except (ValueError, KeyError):
            return None

        # For close signals, we need to determine the symbol from context
        # Since the close signal doesn't include symbol, we use the first valid symbol
        # or a default. This may need to be enhanced based on actual requirements.
        symbol = self.valid_symbols[0] if self.valid_symbols else "XAUUSD"

        return Signal(
            action=action,
            symbol=symbol,
            close_price=close_price,
            timestamp=datetime.now(),
        )

    def is_valid_signal(self, message: str) -> bool:
        """Check if message is a valid signal.

        Args:
            message: Alert message string.

        Returns:
            True if valid signal, False otherwise.
        """
        return self.parse(message) is not None
