"""Configuration management module."""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

import yaml


@dataclass
class SymbolConfig:
    """Configuration for a trading symbol."""

    enabled: bool = True
    lot_size: float = 0.01
    weekend_stop: bool = False


@dataclass
class MT4Config:
    """MT4 configuration."""

    alert_log_path: str = ""


@dataclass
class MT5Config:
    """MT5 configuration."""

    login: int = 0
    password: str = ""
    server: str = ""


@dataclass
class TradeControlConfig:
    """Trade control configuration for MT4 EA integration."""

    enabled: bool = True  # Whether to use trade control file
    control_file_path: str = ""  # Path to trade_control.json
    default_enabled: bool = True  # Default state when file not found


@dataclass
class TradingConfig:
    """Trading configuration."""

    duplicate_threshold_seconds: int = 180  # 3 minutes
    max_execution_delay_seconds: int = 1


@dataclass
class LoggingConfig:
    """Logging configuration."""

    level: str = "INFO"
    file_path: str = "logs/trading.log"
    rotation: str = "daily"


@dataclass
class Config:
    """Main configuration container."""

    mt4: MT4Config = field(default_factory=MT4Config)
    mt5: MT5Config = field(default_factory=MT5Config)
    symbols: dict[str, SymbolConfig] = field(default_factory=dict)
    trading: TradingConfig = field(default_factory=TradingConfig)
    trade_control: TradeControlConfig = field(default_factory=TradeControlConfig)
    logging: LoggingConfig = field(default_factory=LoggingConfig)

    @classmethod
    def from_yaml(cls, path: str | Path) -> "Config":
        """Load configuration from YAML file.

        Args:
            path: Path to YAML configuration file.

        Returns:
            Config instance.

        Raises:
            FileNotFoundError: If config file doesn't exist.
            ValueError: If config file is invalid.
        """
        path = Path(path)
        if not path.exists():
            raise FileNotFoundError(f"Configuration file not found: {path}")

        with open(path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)

        if not data:
            raise ValueError("Configuration file is empty")

        return cls._from_dict(data)

    @classmethod
    def _from_dict(cls, data: dict[str, Any]) -> "Config":
        """Create Config from dictionary."""
        config = cls()

        # MT4 config
        if "mt4" in data:
            config.mt4 = MT4Config(**data["mt4"])

        # MT5 config
        if "mt5" in data:
            config.mt5 = MT5Config(**data["mt5"])

        # Symbols config
        if "symbols" in data:
            for symbol, symbol_data in data["symbols"].items():
                config.symbols[symbol] = SymbolConfig(**symbol_data)

        # Trading config
        if "trading" in data:
            config.trading = TradingConfig(**data["trading"])

        # Trade control config
        if "trade_control" in data:
            config.trade_control = TradeControlConfig(**data["trade_control"])

        # Logging config
        if "logging" in data:
            config.logging = LoggingConfig(**data["logging"])

        return config

    def get_enabled_symbols(self) -> list[str]:
        """Get list of enabled symbols.

        Returns:
            List of enabled symbol names.
        """
        return [symbol for symbol, cfg in self.symbols.items() if cfg.enabled]

    def get_symbol_config(self, symbol: str) -> Optional[SymbolConfig]:
        """Get configuration for specific symbol.

        Args:
            symbol: Symbol name.

        Returns:
            SymbolConfig if found, None otherwise.
        """
        return self.symbols.get(symbol)
