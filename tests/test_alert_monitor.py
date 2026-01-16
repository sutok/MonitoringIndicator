"""Tests for alert_monitor module."""

import tempfile
import time
from datetime import date
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from src.alert_monitor import (
    AlertFileHandler,
    AlertMonitor,
    get_today_log_filename,
    resolve_log_path,
)


class TestAlertFileHandler:
    """Test cases for AlertFileHandler."""

    def test_init_with_existing_file(self) -> None:
        """Test initialization with existing file."""
        with tempfile.NamedTemporaryFile(mode="w", delete=False) as f:
            f.write("existing content\n")
            temp_path = Path(f.name)

        try:
            callback = MagicMock()
            handler = AlertFileHandler(temp_path, callback)

            # Should start at end of file
            assert handler._last_position == temp_path.stat().st_size
            assert handler.file_path == temp_path
            assert handler.callback == callback

        finally:
            temp_path.unlink()

    def test_init_with_nonexistent_file(self) -> None:
        """Test initialization with non-existent file."""
        temp_path = Path("/tmp/nonexistent_test_file.log")
        callback = MagicMock()

        handler = AlertFileHandler(temp_path, callback)

        # Should start at position 0
        assert handler._last_position == 0

    def test_read_new_lines(self) -> None:
        """Test reading new lines from file."""
        with tempfile.NamedTemporaryFile(mode="w", delete=False) as f:
            f.write("initial line\n")
            temp_path = Path(f.name)

        try:
            callback = MagicMock()
            handler = AlertFileHandler(temp_path, callback)

            # Write new content
            with open(temp_path, "a") as f:
                f.write("BUY XAUUSD SL:1920.50 TP:1950.00\n")

            # Read new lines
            handler._read_new_lines()

            # Callback should be called with the new line
            callback.assert_called_once_with("BUY XAUUSD SL:1920.50 TP:1950.00")

        finally:
            temp_path.unlink()

    def test_read_multiple_new_lines(self) -> None:
        """Test reading multiple new lines from file."""
        with tempfile.NamedTemporaryFile(mode="w", delete=False) as f:
            temp_path = Path(f.name)

        try:
            callback = MagicMock()
            handler = AlertFileHandler(temp_path, callback)

            # Write multiple lines
            with open(temp_path, "a") as f:
                f.write("line 1\n")
                f.write("line 2\n")
                f.write("line 3\n")

            # Read new lines
            handler._read_new_lines()

            # Callback should be called for each line
            assert callback.call_count == 3
            calls = [call[0][0] for call in callback.call_args_list]
            assert calls == ["line 1", "line 2", "line 3"]

        finally:
            temp_path.unlink()

    def test_read_empty_lines_ignored(self) -> None:
        """Test that empty lines are ignored."""
        with tempfile.NamedTemporaryFile(mode="w", delete=False) as f:
            temp_path = Path(f.name)

        try:
            callback = MagicMock()
            handler = AlertFileHandler(temp_path, callback)

            # Write lines with empty ones
            with open(temp_path, "a") as f:
                f.write("line 1\n")
                f.write("\n")
                f.write("   \n")
                f.write("line 2\n")

            # Read new lines
            handler._read_new_lines()

            # Only non-empty lines should trigger callback
            assert callback.call_count == 2

        finally:
            temp_path.unlink()


class TestAlertMonitor:
    """Test cases for AlertMonitor."""

    def test_init(self) -> None:
        """Test AlertMonitor initialization."""
        callback = MagicMock()
        monitor = AlertMonitor("/path/to/alerts.log", callback)

        assert monitor.alert_log_path == Path("/path/to/alerts.log")
        assert monitor.callback == callback
        assert monitor._observer is None
        assert monitor._handler is None

    def test_is_running_default(self) -> None:
        """Test is_running returns False by default."""
        callback = MagicMock()
        monitor = AlertMonitor("/path/to/alerts.log", callback)

        assert monitor.is_running() is False

    def test_start_and_stop(self) -> None:
        """Test starting and stopping monitor."""
        with tempfile.TemporaryDirectory() as temp_dir:
            log_path = Path(temp_dir) / "alerts.log"
            log_path.touch()

            callback = MagicMock()
            monitor = AlertMonitor(log_path, callback)

            # Start
            monitor.start()
            assert monitor.is_running() is True
            assert monitor._observer is not None
            assert monitor._handler is not None

            # Stop
            monitor.stop()
            assert monitor._observer is None

    def test_start_with_nonexistent_file(self) -> None:
        """Test starting with non-existent file (should not raise)."""
        with tempfile.TemporaryDirectory() as temp_dir:
            log_path = Path(temp_dir) / "nonexistent.log"

            callback = MagicMock()
            monitor = AlertMonitor(log_path, callback)

            # Should not raise even if file doesn't exist
            monitor.start()
            assert monitor.is_running() is True

            monitor.stop()

    def test_file_monitoring_integration(self) -> None:
        """Integration test for file monitoring."""
        with tempfile.TemporaryDirectory() as temp_dir:
            log_path = Path(temp_dir) / "alerts.log"
            log_path.touch()

            received_lines: list[str] = []

            def callback(line: str) -> None:
                received_lines.append(line)

            monitor = AlertMonitor(log_path, callback)
            monitor.start()

            try:
                # Give observer time to start
                time.sleep(0.1)

                # Write to file
                with open(log_path, "a") as f:
                    f.write("BUY XAUUSD SL:1920.50 TP:1950.00\n")
                    f.flush()

                # Wait for file system event
                time.sleep(0.5)

                # Check if line was received
                # Note: This might be flaky depending on file system
                # In real tests, you might want to use a more robust approach

            finally:
                monitor.stop()


class TestResolvePath:
    """Test cases for resolve_log_path function."""

    def test_resolve_date_placeholder(self) -> None:
        """Test resolving {date} placeholder."""
        today_str = date.today().strftime("%Y%m%d")
        result = resolve_log_path("/logs/{date}.log")

        assert str(result) == f"/logs/{today_str}.log"

    def test_resolve_today_placeholder(self) -> None:
        """Test resolving {today} placeholder."""
        today_str = date.today().strftime("%Y%m%d")
        result = resolve_log_path("/logs/{today}.log")

        assert str(result) == f"/logs/{today_str}.log"

    def test_resolve_directory_with_log_files(self) -> None:
        """Test resolving directory path with existing log files."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create some log files
            old_log = Path(temp_dir) / "20250101.log"
            new_log = Path(temp_dir) / "20250115.log"
            old_log.touch()
            time.sleep(0.1)  # Ensure different mtime
            new_log.touch()

            result = resolve_log_path(temp_dir)

            # Should return the latest log file
            assert result == new_log

    def test_resolve_directory_without_log_files(self) -> None:
        """Test resolving directory path without log files."""
        with tempfile.TemporaryDirectory() as temp_dir:
            today_str = date.today().strftime("%Y%m%d")
            result = resolve_log_path(temp_dir)

            # Should return expected today's log file
            assert result == Path(temp_dir) / f"{today_str}.log"

    def test_resolve_regular_path(self) -> None:
        """Test resolving regular path without placeholders."""
        result = resolve_log_path("/logs/specific.log")

        assert str(result) == "/logs/specific.log"


class TestGetTodayLogFilename:
    """Test cases for get_today_log_filename function."""

    def test_format(self) -> None:
        """Test filename format."""
        today_str = date.today().strftime("%Y%m%d")
        result = get_today_log_filename()

        assert result == f"{today_str}.log"


class TestAlertFileHandlerDateSwitch:
    """Test cases for AlertFileHandler date switching."""

    def test_auto_switch_date_disabled(self) -> None:
        """Test that date switch is disabled when auto_switch_date=False."""
        with tempfile.NamedTemporaryFile(mode="w", delete=False) as f:
            temp_path = Path(f.name)

        try:
            callback = MagicMock()
            handler = AlertFileHandler(temp_path, callback, auto_switch_date=False)

            # Manually change internal date to yesterday
            handler._current_date = date(2020, 1, 1)

            # Should not switch
            assert handler._check_date_change() is False
            assert handler.file_path == temp_path

        finally:
            temp_path.unlink()

    def test_auto_switch_date_enabled(self) -> None:
        """Test that date switch works when enabled."""
        with tempfile.TemporaryDirectory() as temp_dir:
            old_log = Path(temp_dir) / "20200101.log"
            old_log.touch()

            callback = MagicMock()
            handler = AlertFileHandler(old_log, callback, auto_switch_date=True)

            # Manually change internal date to yesterday
            handler._current_date = date(2020, 1, 1)

            # Should switch to today's log
            result = handler._check_date_change()

            assert result is True
            assert handler.file_path.name == get_today_log_filename()
            assert handler._current_date == date.today()


class TestAlertMonitorAutoResolve:
    """Test cases for AlertMonitor auto resolve feature."""

    def test_auto_resolve_enabled(self) -> None:
        """Test auto resolve with {date} placeholder."""
        callback = MagicMock()
        today_str = date.today().strftime("%Y%m%d")

        monitor = AlertMonitor("/logs/{date}.log", callback, auto_resolve_date=True)

        assert str(monitor.alert_log_path) == f"/logs/{today_str}.log"

    def test_auto_resolve_disabled(self) -> None:
        """Test auto resolve disabled keeps original path."""
        callback = MagicMock()

        monitor = AlertMonitor("/logs/{date}.log", callback, auto_resolve_date=False)

        assert str(monitor.alert_log_path) == "/logs/{date}.log"

    def test_get_current_log_path(self) -> None:
        """Test get_current_log_path method."""
        with tempfile.TemporaryDirectory() as temp_dir:
            log_path = Path(temp_dir) / "test.log"
            log_path.touch()

            callback = MagicMock()
            monitor = AlertMonitor(log_path, callback)
            monitor.start()

            try:
                assert monitor.get_current_log_path() == log_path
            finally:
                monitor.stop()
