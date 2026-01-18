"""Tests for config module."""

import tempfile
from pathlib import Path

import pytest
import yaml

from src.config import (
    Config,
    LoggingConfig,
    MT4Config,
    MT5Config,
    SymbolConfig,
    TradingConfig,
)


class TestSymbolConfig:
    """Test cases for SymbolConfig."""

    def test_default_values(self) -> None:
        """Test default values."""
        config = SymbolConfig()
        assert config.enabled is True
        assert config.lot_size == 0.01
        assert config.weekend_stop is False

    def test_custom_values(self) -> None:
        """Test custom values."""
        config = SymbolConfig(enabled=False, lot_size=0.1, weekend_stop=True)
        assert config.enabled is False
        assert config.lot_size == 0.1
        assert config.weekend_stop is True


class TestMT4Config:
    """Test cases for MT4Config."""

    def test_default_values(self) -> None:
        """Test default values."""
        config = MT4Config()
        assert config.alert_log_path == ""

    def test_custom_values(self) -> None:
        """Test custom values."""
        config = MT4Config(alert_log_path="/path/to/logs")
        assert config.alert_log_path == "/path/to/logs"


class TestMT5Config:
    """Test cases for MT5Config."""

    def test_default_values(self) -> None:
        """Test default values."""
        config = MT5Config()
        assert config.login == 0
        assert config.password == ""
        assert config.server == ""

    def test_custom_values(self) -> None:
        """Test custom values."""
        config = MT5Config(login=12345, password="secret", server="TestServer")
        assert config.login == 12345
        assert config.password == "secret"
        assert config.server == "TestServer"


class TestTradingConfig:
    """Test cases for TradingConfig."""

    def test_default_values(self) -> None:
        """Test default values."""
        config = TradingConfig()
        assert config.duplicate_threshold_seconds == 180
        assert config.max_execution_delay_seconds == 1


class TestLoggingConfig:
    """Test cases for LoggingConfig."""

    def test_default_values(self) -> None:
        """Test default values."""
        config = LoggingConfig()
        assert config.level == "INFO"
        assert config.file_path == "logs/trading.log"
        assert config.rotation == "daily"


class TestConfig:
    """Test cases for Config."""

    def test_default_config(self) -> None:
        """Test default configuration."""
        config = Config()
        assert isinstance(config.mt4, MT4Config)
        assert isinstance(config.mt5, MT5Config)
        assert isinstance(config.trading, TradingConfig)
        assert isinstance(config.logging, LoggingConfig)
        assert config.symbols == {}

    def test_from_yaml(self) -> None:
        """Test loading from YAML file."""
        yaml_content = """
mt4:
  alert_log_path: "/path/to/logs"

mt5:
  login: 12345678
  password: "test_password"
  server: "TestServer-Live"

symbols:
  XAUUSD:
    enabled: true
    lot_size: 0.02
    weekend_stop: true
  BTCUSD:
    enabled: true
    lot_size: 0.01
    weekend_stop: false

trading:
  duplicate_threshold_seconds: 300
  max_execution_delay_seconds: 2

logging:
  level: DEBUG
  file_path: "logs/debug.log"
  rotation: daily
"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write(yaml_content)
            temp_path = f.name

        try:
            config = Config.from_yaml(temp_path)

            # MT4
            assert config.mt4.alert_log_path == "/path/to/logs"

            # MT5
            assert config.mt5.login == 12345678
            assert config.mt5.password == "test_password"
            assert config.mt5.server == "TestServer-Live"

            # Symbols
            assert "XAUUSD" in config.symbols
            assert "BTCUSD" in config.symbols
            assert config.symbols["XAUUSD"].lot_size == 0.02
            assert config.symbols["XAUUSD"].weekend_stop is True
            assert config.symbols["BTCUSD"].weekend_stop is False

            # Trading
            assert config.trading.duplicate_threshold_seconds == 300
            assert config.trading.max_execution_delay_seconds == 2

            # Logging
            assert config.logging.level == "DEBUG"
            assert config.logging.file_path == "logs/debug.log"

        finally:
            Path(temp_path).unlink()

    def test_from_yaml_file_not_found(self) -> None:
        """Test loading from non-existent file."""
        with pytest.raises(FileNotFoundError):
            Config.from_yaml("/non/existent/path.yaml")

    def test_from_yaml_empty_file(self) -> None:
        """Test loading from empty file."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write("")
            temp_path = f.name

        try:
            with pytest.raises(ValueError, match="empty"):
                Config.from_yaml(temp_path)
        finally:
            Path(temp_path).unlink()

    def test_get_enabled_symbols(self) -> None:
        """Test get_enabled_symbols method."""
        config = Config()
        config.symbols = {
            "XAUUSD": SymbolConfig(enabled=True),
            "BTCUSD": SymbolConfig(enabled=False),
            "ETHUSD": SymbolConfig(enabled=True),
        }

        enabled = config.get_enabled_symbols()
        assert "XAUUSD" in enabled
        assert "ETHUSD" in enabled
        assert "BTCUSD" not in enabled

    def test_get_symbol_config(self) -> None:
        """Test get_symbol_config method."""
        config = Config()
        config.symbols = {
            "XAUUSD": SymbolConfig(lot_size=0.05),
        }

        # Existing symbol
        symbol_config = config.get_symbol_config("XAUUSD")
        assert symbol_config is not None
        assert symbol_config.lot_size == 0.05

        # Non-existing symbol
        assert config.get_symbol_config("UNKNOWN") is None

    def test_partial_yaml(self) -> None:
        """Test loading partial YAML (only some sections)."""
        yaml_content = """
mt5:
  login: 99999
  password: "partial"
  server: "PartialServer"
"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write(yaml_content)
            temp_path = f.name

        try:
            config = Config.from_yaml(temp_path)

            # MT5 should be loaded
            assert config.mt5.login == 99999

            # Others should have defaults
            assert config.mt4.alert_log_path == ""
            assert config.trading.duplicate_threshold_seconds == 180

        finally:
            Path(temp_path).unlink()
