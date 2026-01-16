"""Tests for trade_control module."""

import json
import tempfile
from datetime import datetime
from pathlib import Path

import pytest

from src.trade_control import TradeController, TradeControlState


class TestTradeControlState:
    """Test cases for TradeControlState."""

    def test_default_values(self) -> None:
        """Test default values."""
        state = TradeControlState(enabled=True)
        assert state.enabled is True
        assert state.updated_at is None
        assert state.source is None

    def test_full_values(self) -> None:
        """Test with all values."""
        now = datetime.now()
        state = TradeControlState(
            enabled=False,
            updated_at=now,
            source="MT4_EA",
        )
        assert state.enabled is False
        assert state.updated_at == now
        assert state.source == "MT4_EA"


class TestTradeController:
    """Test cases for TradeController."""

    def test_file_not_found_returns_default(self) -> None:
        """Test that missing file returns default enabled state."""
        controller = TradeController("/nonexistent/path/control.json")
        assert controller.is_trade_enabled() is True

    def test_file_not_found_returns_custom_default(self) -> None:
        """Test that missing file returns custom default state."""
        controller = TradeController("/nonexistent/path/control.json")
        controller.set_default_enabled(False)
        assert controller.is_trade_enabled() is False

    def test_read_enabled_true(self) -> None:
        """Test reading enabled=true from file."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump({"enabled": True}, f)
            temp_path = f.name

        try:
            controller = TradeController(temp_path)
            assert controller.is_trade_enabled() is True
        finally:
            Path(temp_path).unlink()

    def test_read_enabled_false(self) -> None:
        """Test reading enabled=false from file."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump({"enabled": False}, f)
            temp_path = f.name

        try:
            controller = TradeController(temp_path)
            assert controller.is_trade_enabled() is False
        finally:
            Path(temp_path).unlink()

    def test_read_full_state(self) -> None:
        """Test reading full state from file."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(
                {
                    "enabled": True,
                    "updated_at": "2024.01.15 10:30:00",
                    "source": "MT4_EA",
                },
                f,
            )
            temp_path = f.name

        try:
            controller = TradeController(temp_path)
            state = controller.read_state()

            assert state is not None
            assert state.enabled is True
            assert state.source == "MT4_EA"
            assert state.updated_at is not None
            assert state.updated_at.year == 2024
        finally:
            Path(temp_path).unlink()

    def test_read_iso_date_format(self) -> None:
        """Test reading ISO date format."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(
                {
                    "enabled": True,
                    "updated_at": "2024-01-15T10:30:00",
                },
                f,
            )
            temp_path = f.name

        try:
            controller = TradeController(temp_path)
            state = controller.read_state()

            assert state is not None
            assert state.updated_at is not None
        finally:
            Path(temp_path).unlink()

    def test_invalid_json_returns_none(self) -> None:
        """Test that invalid JSON returns None."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            f.write("not valid json {")
            temp_path = f.name

        try:
            controller = TradeController(temp_path)
            state = controller.read_state()
            assert state is None
            # Should fall back to default
            assert controller.is_trade_enabled() is True
        finally:
            Path(temp_path).unlink()

    def test_missing_enabled_key_uses_default(self) -> None:
        """Test that missing enabled key uses default."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump({"source": "test"}, f)
            temp_path = f.name

        try:
            controller = TradeController(temp_path)
            # Default is True
            assert controller.is_trade_enabled() is True
        finally:
            Path(temp_path).unlink()

    def test_last_state_property(self) -> None:
        """Test last_state property."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump({"enabled": False}, f)
            temp_path = f.name

        try:
            controller = TradeController(temp_path)
            assert controller.last_state is None

            controller.read_state()
            assert controller.last_state is not None
            assert controller.last_state.enabled is False
        finally:
            Path(temp_path).unlink()

    def test_state_change_detected(self) -> None:
        """Test that state changes are tracked."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump({"enabled": True}, f)
            temp_path = f.name

        try:
            controller = TradeController(temp_path)

            # First read
            state1 = controller.read_state()
            assert state1 is not None
            assert state1.enabled is True

            # Update file
            with open(temp_path, "w") as f:
                json.dump({"enabled": False}, f)

            # Second read
            state2 = controller.read_state()
            assert state2 is not None
            assert state2.enabled is False

        finally:
            Path(temp_path).unlink()

    def test_path_as_string_or_path(self) -> None:
        """Test that both string and Path work."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump({"enabled": True}, f)
            temp_path = f.name

        try:
            # String path
            controller1 = TradeController(temp_path)
            assert controller1.is_trade_enabled() is True

            # Path object
            controller2 = TradeController(Path(temp_path))
            assert controller2.is_trade_enabled() is True
        finally:
            Path(temp_path).unlink()
