"""Trade control module for reading MT4 EA control flags."""

import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Optional

from .logger import logger


@dataclass
class TradeControlState:
    """Trade control state from MT4 EA."""

    enabled: bool
    updated_at: Optional[datetime] = None
    source: Optional[str] = None


class TradeController:
    """Controller for reading trade enable/disable flags from MT4 EA.

    This class reads a JSON control file that is written by the MT4 EA
    (TradeController.mq4) to determine if trade execution should be enabled.
    """

    def __init__(self, control_file_path: str | Path):
        """Initialize trade controller.

        Args:
            control_file_path: Path to the trade control JSON file.
        """
        self.control_file_path = Path(control_file_path)
        self._last_state: Optional[TradeControlState] = None
        self._default_enabled = True  # Default to enabled if file not found

    def is_trade_enabled(self) -> bool:
        """Check if trade execution is enabled.

        Returns:
            True if trading is enabled, False otherwise.
            Returns default_enabled value if control file cannot be read.
        """
        state = self.read_state()
        return state.enabled if state else self._default_enabled

    def read_state(self) -> Optional[TradeControlState]:
        """Read the current trade control state from file.

        Returns:
            TradeControlState if file can be read, None otherwise.
        """
        if not self.control_file_path.exists():
            logger.debug(
                f"Trade control file not found: {self.control_file_path}. "
                f"Using default: enabled={self._default_enabled}"
            )
            return None

        try:
            content = self.control_file_path.read_text(encoding="utf-8")
            data = json.loads(content)

            # Parse updated_at if present
            updated_at = None
            if "updated_at" in data:
                try:
                    # MT4 format: "YYYY.MM.DD HH:MM:SS"
                    updated_at = datetime.strptime(
                        data["updated_at"], "%Y.%m.%d %H:%M:%S"
                    )
                except ValueError:
                    # Try alternative formats
                    try:
                        updated_at = datetime.fromisoformat(data["updated_at"])
                    except ValueError:
                        pass

            state = TradeControlState(
                enabled=data.get("enabled", self._default_enabled),
                updated_at=updated_at,
                source=data.get("source"),
            )

            # Log state change
            if self._last_state is None or self._last_state.enabled != state.enabled:
                status = "ENABLED" if state.enabled else "DISABLED"
                logger.info(f"Trade control state: {status}")

            self._last_state = state
            return state

        except json.JSONDecodeError as e:
            logger.warning(f"Invalid JSON in trade control file: {e}")
            return None
        except OSError as e:
            logger.warning(f"Error reading trade control file: {e}")
            return None

    def set_default_enabled(self, enabled: bool) -> None:
        """Set the default enabled state when control file is not available.

        Args:
            enabled: Default enabled state.
        """
        self._default_enabled = enabled
        logger.debug(f"Trade control default set to: {enabled}")

    @property
    def last_state(self) -> Optional[TradeControlState]:
        """Get the last read state.

        Returns:
            Last TradeControlState or None if never read.
        """
        return self._last_state
