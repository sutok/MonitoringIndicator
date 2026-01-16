"""Main entry point for MonitoringIndicator."""

import argparse
import signal
import sys
import time
from pathlib import Path
from types import FrameType
from typing import Optional

from .alert_monitor import AlertMonitor
from .config import Config
from .logger import logger, setup_logger
from .order_executor import OrderExecutor
from .signal_parser import SignalParser


class MonitoringIndicator:
    """Main application class."""

    def __init__(self, config_path: str | Path):
        """Initialize application.

        Args:
            config_path: Path to configuration file.
        """
        self.config = Config.from_yaml(config_path)
        self._setup_logging()

        self.signal_parser = SignalParser(
            valid_symbols=self.config.get_enabled_symbols()
        )
        self.order_executor = OrderExecutor(self.config)
        self.alert_monitor = AlertMonitor(
            self.config.mt4.alert_log_path,
            self._on_alert,
        )
        self._running = False

    def _setup_logging(self) -> None:
        """Set up logging based on configuration."""
        import logging

        level = getattr(logging, self.config.logging.level.upper(), logging.INFO)
        setup_logger(
            name="monitoring_indicator",
            log_file=self.config.logging.file_path,
            level=level,
        )

    def _on_alert(self, message: str) -> None:
        """Handle new alert message.

        Args:
            message: Alert message from MT4.
        """
        logger.debug(f"Received alert: {message}")

        # Parse signal
        parsed_signal = self.signal_parser.parse(message)
        if not parsed_signal:
            logger.debug(f"Ignored non-signal message: {message}")
            return

        logger.info(f"Signal detected: {parsed_signal}")

        # Execute order
        result = self.order_executor.execute(parsed_signal)

        if result.success:
            logger.info(f"Order successful: Ticket={result.order_ticket}")
        else:
            logger.warning(f"Order failed: {result.error_message}")

    def start(self) -> None:
        """Start the monitoring system."""
        logger.info("Starting MonitoringIndicator...")

        # Connect to MT5
        if not self.order_executor.connect():
            logger.error("Failed to connect to MT5. Exiting.")
            sys.exit(1)

        # Start alert monitoring
        self.alert_monitor.start()
        self._running = True

        logger.info("MonitoringIndicator started successfully")
        logger.info(f"Monitoring symbols: {self.config.get_enabled_symbols()}")

    def stop(self) -> None:
        """Stop the monitoring system."""
        logger.info("Stopping MonitoringIndicator...")
        self._running = False

        self.alert_monitor.stop()
        self.order_executor.disconnect()

        logger.info("MonitoringIndicator stopped")

    def run(self) -> None:
        """Run the main loop."""
        self.start()

        try:
            while self._running:
                time.sleep(1)
        except KeyboardInterrupt:
            logger.info("Keyboard interrupt received")
        finally:
            self.stop()


def main() -> None:
    """Main entry point."""
    parser = argparse.ArgumentParser(description="MT4 Alert to MT5 Order System")
    parser.add_argument(
        "-c",
        "--config",
        default="config/settings.yaml",
        help="Path to configuration file",
    )
    args = parser.parse_args()

    # Handle signals for graceful shutdown
    app: MonitoringIndicator | None = None

    def signal_handler(signum: int, frame: Optional[FrameType]) -> None:
        logger.info(f"Received signal {signum}")
        if app:
            app.stop()
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    # Start application
    try:
        app = MonitoringIndicator(args.config)
        app.run()
    except FileNotFoundError as e:
        logger.error(f"Configuration error: {e}")
        sys.exit(1)
    except Exception as e:
        logger.exception(f"Unexpected error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
