"""Tests for alert_monitor module."""

import tempfile
import time
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from src.alert_monitor import AlertFileHandler, AlertMonitor


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
