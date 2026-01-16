"""MT5 order execution module."""

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Optional

from .config import Config, SymbolConfig
from .logger import logger
from .signal_parser import Signal, SignalAction

# MT5 import with fallback for non-Windows environments
try:
    import MetaTrader5 as mt5

    MT5_AVAILABLE = True
except ImportError:
    MT5_AVAILABLE = False
    mt5 = None  # type: ignore


@dataclass
class OrderResult:
    """Result of order execution."""

    success: bool
    order_ticket: Optional[int] = None
    error_message: Optional[str] = None
    executed_at: Optional[datetime] = None


class DuplicateChecker:
    """Check for duplicate signals within threshold."""

    def __init__(self, threshold_seconds: int = 180):
        """Initialize duplicate checker.

        Args:
            threshold_seconds: Time threshold in seconds for duplicate detection.
        """
        self.threshold_seconds = threshold_seconds
        self._last_signals: dict[str, datetime] = {}

    def is_duplicate(self, signal: Signal) -> bool:
        """Check if signal is a duplicate.

        Args:
            signal: Signal to check.

        Returns:
            True if duplicate, False otherwise.
        """
        key = f"{signal.symbol}_{signal.action.value}"
        now = datetime.now()

        if key in self._last_signals:
            last_time = self._last_signals[key]
            if now - last_time < timedelta(seconds=self.threshold_seconds):
                return True

        self._last_signals[key] = now
        return False

    def clear(self) -> None:
        """Clear all recorded signals."""
        self._last_signals.clear()


class TradingTimeChecker:
    """Check if trading is allowed based on time restrictions."""

    @staticmethod
    def is_weekend() -> bool:
        """Check if current time is weekend (Saturday or Sunday).

        Returns:
            True if weekend, False otherwise.
        """
        now = datetime.now()
        # weekday(): Monday=0, Sunday=6
        return now.weekday() >= 5

    def can_trade(self, symbol: str, symbol_config: SymbolConfig) -> bool:
        """Check if trading is allowed for symbol.

        Args:
            symbol: Symbol name.
            symbol_config: Symbol configuration.

        Returns:
            True if trading allowed, False otherwise.
        """
        if not symbol_config.enabled:
            return False

        if symbol_config.weekend_stop and self.is_weekend():
            logger.info(f"Trading disabled for {symbol} during weekend")
            return False

        return True


class OrderExecutor:
    """Execute orders on MT5."""

    def __init__(self, config: Config):
        """Initialize order executor.

        Args:
            config: Application configuration.
        """
        self.config = config
        self.duplicate_checker = DuplicateChecker(
            config.trading.duplicate_threshold_seconds
        )
        self.time_checker = TradingTimeChecker()
        self._connected = False

    def connect(self) -> bool:
        """Connect to MT5 terminal.

        Returns:
            True if connected successfully, False otherwise.
        """
        if not MT5_AVAILABLE:
            logger.error("MetaTrader5 package not available (Windows only)")
            return False

        if not mt5.initialize():
            logger.error(f"MT5 initialization failed: {mt5.last_error()}")
            return False

        authorized = mt5.login(
            self.config.mt5.login,
            password=self.config.mt5.password,
            server=self.config.mt5.server,
        )

        if not authorized:
            logger.error(f"MT5 login failed: {mt5.last_error()}")
            mt5.shutdown()
            return False

        self._connected = True
        logger.info(f"Connected to MT5: {self.config.mt5.server}")
        return True

    def disconnect(self) -> None:
        """Disconnect from MT5 terminal."""
        if MT5_AVAILABLE and self._connected:
            mt5.shutdown()
            self._connected = False
            logger.info("Disconnected from MT5")

    def is_connected(self) -> bool:
        """Check if connected to MT5.

        Returns:
            True if connected, False otherwise.
        """
        return self._connected

    def execute(self, signal: Signal) -> OrderResult:
        """Execute order based on signal.

        Args:
            signal: Trading signal to execute.

        Returns:
            OrderResult with execution details.
        """
        # Check duplicate
        if self.duplicate_checker.is_duplicate(signal):
            logger.warning(f"Duplicate signal ignored: {signal}")
            return OrderResult(
                success=False,
                error_message="Duplicate signal within threshold",
            )

        # Check symbol config
        symbol_config = self.config.get_symbol_config(signal.symbol)
        if not symbol_config:
            logger.warning(f"Unknown symbol: {signal.symbol}")
            return OrderResult(
                success=False,
                error_message=f"Unknown symbol: {signal.symbol}",
            )

        # Check trading time
        if not self.time_checker.can_trade(signal.symbol, symbol_config):
            return OrderResult(
                success=False,
                error_message="Trading not allowed at this time",
            )

        # Check connection
        if not self._connected:
            logger.error("Not connected to MT5")
            return OrderResult(
                success=False,
                error_message="Not connected to MT5",
            )

        # Execute order
        return self._send_order(signal, symbol_config)

    def _send_order(
        self,
        signal: Signal,
        symbol_config: SymbolConfig,
    ) -> OrderResult:
        """Send order to MT5.

        Args:
            signal: Trading signal.
            symbol_config: Symbol configuration.

        Returns:
            OrderResult with execution details.
        """
        if not MT5_AVAILABLE:
            return OrderResult(
                success=False,
                error_message="MT5 not available",
            )

        # Get symbol info
        symbol_info = mt5.symbol_info(signal.symbol)
        if symbol_info is None:
            return OrderResult(
                success=False,
                error_message=f"Symbol not found: {signal.symbol}",
            )

        if not symbol_info.visible:
            if not mt5.symbol_select(signal.symbol, True):
                return OrderResult(
                    success=False,
                    error_message=f"Failed to select symbol: {signal.symbol}",
                )

        # Determine order type
        if signal.action == SignalAction.BUY:
            order_type = mt5.ORDER_TYPE_BUY
            price = mt5.symbol_info_tick(signal.symbol).ask
        else:
            order_type = mt5.ORDER_TYPE_SELL
            price = mt5.symbol_info_tick(signal.symbol).bid

        # Prepare request
        request = {
            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": signal.symbol,
            "volume": symbol_config.lot_size,
            "type": order_type,
            "price": price,
            "sl": signal.stop_loss,
            "tp": signal.take_profit,
            "deviation": 20,
            "magic": 123456,
            "comment": "MonitoringIndicator",
            "type_time": mt5.ORDER_TIME_GTC,
            "type_filling": mt5.ORDER_FILLING_IOC,
        }

        # Send order
        result = mt5.order_send(request)

        if result.retcode != mt5.TRADE_RETCODE_DONE:
            error_msg = f"Order failed: {result.retcode} - {result.comment}"
            logger.error(error_msg)
            return OrderResult(
                success=False,
                error_message=error_msg,
            )

        logger.info(
            f"Order executed: {signal.action.value} {signal.symbol} "
            f"Lot:{symbol_config.lot_size} Ticket:{result.order}"
        )

        return OrderResult(
            success=True,
            order_ticket=result.order,
            executed_at=datetime.now(),
        )
