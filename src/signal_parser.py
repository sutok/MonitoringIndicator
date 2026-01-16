"""Signal parsing module for MT4 alert messages."""

import re
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Optional


class SignalAction(Enum):
    """Trading signal action type."""

    BUY = "BUY"
    SELL = "SELL"


@dataclass
class Signal:
    """Parsed trading signal."""

    action: SignalAction
    symbol: str
    stop_loss: float
    take_profit: float
    timestamp: datetime

    def __str__(self) -> str:
        """Return string representation."""
        return (
            f"{self.action.value} {self.symbol} "
            f"SL:{self.stop_loss} TP:{self.take_profit}"
        )


class SignalParser:
    """Parser for MT4 alert messages."""

    # Pattern: BUY XAUUSD SL:1920.50 TP:1950.00
    SIGNAL_PATTERN = re.compile(
        r"^(BUY|SELL)\s+(\w+)\s+SL:([\d.]+)\s+TP:([\d.]+)$",
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

        match = self.SIGNAL_PATTERN.match(message)
        if not match:
            return None

        action_str, symbol, sl_str, tp_str = match.groups()

        # Validate symbol
        symbol = symbol.upper()
        if self.valid_symbols and symbol not in self.valid_symbols:
            return None

        try:
            action = SignalAction(action_str.upper())
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

    def is_valid_signal(self, message: str) -> bool:
        """Check if message is a valid signal.

        Args:
            message: Alert message string.

        Returns:
            True if valid signal, False otherwise.
        """
        return self.parse(message) is not None
