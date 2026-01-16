"""MT4 Alert log file monitoring module."""

from pathlib import Path
from typing import Any, Callable, Optional

from watchdog.events import (FileModifiedEvent, FileSystemEvent,
                             FileSystemEventHandler)
from watchdog.observers import Observer

from .logger import logger


class AlertFileHandler(FileSystemEventHandler):
    """Handler for alert log file changes."""

    def __init__(
        self,
        file_path: Path,
        callback: Callable[[str], None],
    ):
        """Initialize handler.

        Args:
            file_path: Path to alert log file.
            callback: Function to call with new alert lines.
        """
        super().__init__()
        self.file_path = file_path
        self.callback = callback
        self._last_position = 0

        # Initialize position to end of file
        if file_path.exists():
            self._last_position = file_path.stat().st_size

    def on_modified(self, event: FileSystemEvent) -> None:
        """Handle file modification event.

        Args:
            event: File system event.
        """
        if not isinstance(event, FileModifiedEvent):
            return

        src_path = event.src_path
        if isinstance(src_path, bytes):
            src_path = src_path.decode("utf-8")

        event_path = Path(src_path)
        if event_path != self.file_path:
            return

        self._read_new_lines()

    def _read_new_lines(self) -> None:
        """Read new lines from file since last position."""
        try:
            with open(self.file_path, "r", encoding="utf-8") as f:
                f.seek(self._last_position)
                new_content = f.read()
                self._last_position = f.tell()

            if new_content:
                for line in new_content.strip().split("\n"):
                    line = line.strip()
                    if line:
                        logger.debug(f"New alert line: {line}")
                        self.callback(line)

        except Exception as e:
            logger.error(f"Error reading alert file: {e}")


class AlertMonitor:
    """Monitor for MT4 alert log file."""

    def __init__(
        self,
        alert_log_path: str | Path,
        callback: Callable[[str], None],
    ):
        """Initialize alert monitor.

        Args:
            alert_log_path: Path to MT4 alert log file.
            callback: Function to call when new alert detected.
        """
        self.alert_log_path = Path(alert_log_path)
        self.callback = callback
        self._observer: Any = None
        self._handler: Optional[AlertFileHandler] = None

    def start(self) -> None:
        """Start monitoring alert log file."""
        if not self.alert_log_path.exists():
            logger.warning(
                f"Alert log file not found: {self.alert_log_path}. "
                "Waiting for file creation..."
            )

        self._handler = AlertFileHandler(self.alert_log_path, self.callback)
        self._observer = Observer()
        self._observer.schedule(
            self._handler,
            str(self.alert_log_path.parent),
            recursive=False,
        )
        self._observer.start()

        logger.info(f"Started monitoring: {self.alert_log_path}")

    def stop(self) -> None:
        """Stop monitoring alert log file."""
        if self._observer:
            self._observer.stop()
            self._observer.join()
            self._observer = None
            logger.info("Stopped alert monitoring")

    def is_running(self) -> bool:
        """Check if monitor is running.

        Returns:
            True if running, False otherwise.
        """
        return self._observer is not None and self._observer.is_alive()
