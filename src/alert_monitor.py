"""MT4 Alert log file monitoring module."""

import re
from datetime import date, datetime
from pathlib import Path
from typing import Any, Callable, Optional

from watchdog.events import (
    FileCreatedEvent,
    FileModifiedEvent,
    FileSystemEvent,
    FileSystemEventHandler,
)
from watchdog.observers import Observer

from .logger import logger


def resolve_log_path(path_pattern: str | Path) -> Path:
    """Resolve log path with date placeholder or auto-detection.

    Supports:
    - {date} placeholder: replaced with today's date (YYYYMMDD)
    - {today} placeholder: same as {date}
    - Directory path: finds the latest .log file

    Args:
        path_pattern: Path pattern with optional placeholders or directory.

    Returns:
        Resolved Path to the log file.

    Examples:
        >>> resolve_log_path("C:/logs/{date}.log")
        Path("C:/logs/20250116.log")

        >>> resolve_log_path("C:/logs/")  # Returns latest .log file
        Path("C:/logs/20250116.log")
    """
    path_str = str(path_pattern)
    today_str = date.today().strftime("%Y%m%d")

    # Replace date placeholders
    path_str = path_str.replace("{date}", today_str)
    path_str = path_str.replace("{today}", today_str)

    resolved_path = Path(path_str)

    # If it's a directory, find the latest log file
    if resolved_path.is_dir():
        log_files = list(resolved_path.glob("*.log"))
        if log_files:
            # Sort by modification time, get the latest
            latest = max(log_files, key=lambda f: f.stat().st_mtime)
            logger.info(f"Auto-detected latest log file: {latest}")
            return latest
        else:
            # Return expected today's log file
            expected = resolved_path / f"{today_str}.log"
            logger.info(f"No log files found, expecting: {expected}")
            return expected

    return resolved_path


def get_today_log_filename() -> str:
    """Get today's log filename in YYYYMMDD.log format.

    Returns:
        Today's log filename.
    """
    return date.today().strftime("%Y%m%d") + ".log"


class AlertFileHandler(FileSystemEventHandler):
    """Handler for alert log file changes."""

    def __init__(
        self,
        file_path: Path,
        callback: Callable[[str], None],
        auto_switch_date: bool = True,
    ):
        """Initialize handler.

        Args:
            file_path: Path to alert log file.
            callback: Function to call with new alert lines.
            auto_switch_date: Auto-switch to new log file at midnight.
        """
        super().__init__()
        self.file_path = file_path
        self.callback = callback
        self.auto_switch_date = auto_switch_date
        self._last_position = 0
        self._current_date = date.today()

        # Initialize position to end of file
        if file_path.exists():
            self._last_position = file_path.stat().st_size

    def _check_date_change(self) -> bool:
        """Check if date has changed and update file path if needed.

        Returns:
            True if date changed, False otherwise.
        """
        if not self.auto_switch_date:
            return False

        today = date.today()
        if today != self._current_date:
            self._current_date = today
            new_filename = get_today_log_filename()
            new_path = self.file_path.parent / new_filename

            logger.info(f"Date changed, switching to: {new_path}")
            self.file_path = new_path
            self._last_position = 0

            if new_path.exists():
                self._last_position = new_path.stat().st_size

            return True
        return False

    def on_modified(self, event: FileSystemEvent) -> None:
        """Handle file modification event.

        Args:
            event: File system event.
        """
        if not isinstance(event, FileModifiedEvent):
            return

        self._check_date_change()

        src_path = event.src_path
        if isinstance(src_path, bytes):
            src_path = src_path.decode("utf-8")

        event_path = Path(src_path)
        if event_path != self.file_path:
            return

        self._read_new_lines()

    def on_created(self, event: FileSystemEvent) -> None:
        """Handle file creation event (for new daily log files).

        Args:
            event: File system event.
        """
        if not isinstance(event, FileCreatedEvent):
            return

        src_path = event.src_path
        if isinstance(src_path, bytes):
            src_path = src_path.decode("utf-8")

        event_path = Path(src_path)

        # Check if this is today's new log file
        if self.auto_switch_date and event_path.name == get_today_log_filename():
            logger.info(f"New daily log file created: {event_path}")
            self.file_path = event_path
            self._last_position = 0
            self._current_date = date.today()

    def _read_new_lines(self) -> None:
        """Read new lines from file since last position.

        Lines ending with backslash (\\) are joined with the next line.
        """
        try:
            if not self.file_path.exists():
                return

            with open(self.file_path, "r", encoding="utf-8") as f:
                f.seek(self._last_position)
                new_content = f.read()
                self._last_position = f.tell()

            if new_content:
                # Split into lines and merge lines ending with backslash
                raw_lines = new_content.strip().split("\n")
                merged_lines = []
                i = 0

                while i < len(raw_lines):
                    line = raw_lines[i].rstrip()

                    # Join lines ending with backslash
                    while line.endswith("\\") and i + 1 < len(raw_lines):
                        line = line[:-1]  # Remove trailing backslash
                        i += 1
                        line += raw_lines[i].strip()  # Append next line

                    merged_lines.append(line)
                    i += 1

                # Process merged lines
                for line in merged_lines:
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
        auto_resolve_date: bool = True,
    ):
        """Initialize alert monitor.

        Args:
            alert_log_path: Path to MT4 alert log file.
                Supports {date} placeholder and directory auto-detection.
            callback: Function to call when new alert detected.
            auto_resolve_date: Auto-resolve {date} placeholder and detect latest log.
        """
        if auto_resolve_date:
            self.alert_log_path = resolve_log_path(alert_log_path)
        else:
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

        self._handler = AlertFileHandler(
            self.alert_log_path,
            self.callback,
            auto_switch_date=True,
        )
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

    def get_current_log_path(self) -> Path:
        """Get the current log file path being monitored.

        Returns:
            Current log file path.
        """
        if self._handler:
            return self._handler.file_path
        return self.alert_log_path
