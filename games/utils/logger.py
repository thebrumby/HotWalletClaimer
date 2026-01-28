"""
Enhanced Logging Framework for HotWalletClaimer
Provides structured logging with different levels, formatting, and file output.
"""

import logging
import sys
from datetime import datetime
from typing import Optional, Dict, Any
import json
from pathlib import Path


class HotWalletClaimerFormatter(logging.Formatter):
    """Custom formatter with rich output including colors and context."""

    # ANSI color codes
    COLORS = {
        'DEBUG': '\033[36m',    # Cyan
        'INFO': '\033[32m',     # Green
        'WARNING': '\033[33m',  # Yellow
        'ERROR': '\033[31m',    # Red
        'CRITICAL': '\033[35m', # Magenta
        'RESET': '\033[0m'
    }

    def __init__(self, include_context: bool = True):
        """Initialize formatter.

        Args:
            include_context: Whether to include file and line number context
        """
        super().__init__()
        self.include_context = include_context

    def format(self, record: logging.LogRecord) -> str:
        """Format log record with colors and context.

        Args:
            record: Log record to format

        Returns:
            Formatted log message
        """
        # Get color for level
        color = self.COLORS.get(record.levelname, self.COLORS['RESET'])
        reset = self.COLORS['RESET']

        # Format level name with color
        levelname = f"{color}{record.levelname}{reset}"

        # Get timestamp
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # Build message
        message = f"[{timestamp}] {levelname} - {record.getMessage()}"

        # Add context if requested
        if self.include_context:
            context = f" (from {record.pathname}:{record.lineno})"
            message += context

        return message


class StructuredLogger:
    """Structured logger for HotWalletClaimer with multiple handlers."""

    def __init__(
        self,
        name: str,
        log_file: Optional[str] = None,
        log_level: int = logging.INFO,
        console_output: bool = True
    ):
        """Initialize structured logger.

        Args:
            name: Logger name (usually __name__)
            log_file: Optional file path for log output
            log_level: Minimum log level to display
            console_output: Whether to output to console
        """
        self.logger = logging.getLogger(name)
        self.logger.setLevel(log_level)

        # Clear existing handlers
        self.logger.handlers.clear()

        # Create formatter
        self.formatter = HotWalletClaimerFormatter(include_context=True)

        # Console handler
        if console_output:
            console_handler = logging.StreamHandler(sys.stdout)
            console_handler.setLevel(log_level)
            console_handler.setFormatter(self.formatter)
            self.logger.addHandler(console_handler)

        # File handler
        if log_file:
            # Ensure log directory exists
            log_path = Path(log_file)
            log_path.parent.mkdir(parents=True, exist_ok=True)

            file_handler = logging.FileHandler(log_file, encoding='utf-8')
            file_handler.setLevel(log_level)
            file_handler.setFormatter(self.formatter)
            self.logger.addHandler(file_handler)

    def debug(self, message: str, **kwargs) -> None:
        """Log debug message."""
        self.logger.debug(message, extra={'context': kwargs})

    def info(self, message: str, **kwargs) -> None:
        """Log info message."""
        self.logger.info(message, extra={'context': kwargs})

    def warning(self, message: str, **kwargs) -> None:
        """Log warning message."""
        self.logger.warning(message, extra={'context': kwargs})

    def error(self, message: str, **kwargs) -> None:
        """Log error message."""
        self.logger.error(message, extra={'context': kwargs})

    def critical(self, message: str, **kwargs) -> None:
        """Log critical message."""
        self.logger.critical(message, extra={'context': kwargs})

    def debug_context(self, context: Dict[str, Any]) -> None:
        """Log debug context (useful for troubleshooting)."""
        self.logger.debug(f"Context: {json.dumps(context, indent=2, default=str)}")

    def info_context(self, context: Dict[str, Any]) -> None:
        """Log info context."""
        self.logger.info(f"Context: {json.dumps(context, indent=2, default=str)}")

    def error_context(self, context: Dict[str, Any]) -> None:
        """Log error context."""
        self.logger.error(f"Context: {json.dumps(context, indent=2, default=str)}")


class LoggerUtils:
    """Utilities for logger initialization."""

    @staticmethod
    def get_game_logger(game_name: str) -> StructuredLogger:
        """Get logger for specific game.

        Args:
            game_name: Name of the game (e.g., 'Hot', 'HamsterKombat')

        Returns:
            StructuredLogger instance
        """
        return StructuredLogger(f"games.{game_name}")

    @staticmethod
    def get_main_logger() -> StructuredLogger:
        """Get main application logger.

        Returns:
            StructuredLogger instance
        """
        return StructuredLogger("HotWalletClaimer")

    @staticmethod
    def setup_common_handlers(logger: logging.Logger, log_file: str) -> None:
        """Setup common handlers for a logger.

        Args:
            logger: Logger to configure
            log_file: Path to log file
        """
        formatter = HotWalletClaimerFormatter(include_context=True)

        # Console handler
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.INFO)
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)

        # File handler
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)

        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)


# Global logger instances
main_logger = StructuredLogger("HotWalletClaimer")

# Game-specific logger instances (created on demand)
_game_loggers = {}

def get_game_logger(game_name: str) -> StructuredLogger:
    """Get game logger, creating if it doesn't exist.

    Args:
        game_name: Name of the game

    Returns:
        Game logger instance
    """
    if game_name not in _game_loggers:
        _game_loggers[game_name] = LoggerUtils.get_game_logger(game_name)
    return _game_loggers[game_name]


def reset_game_loggers() -> None:
    """Reset all game loggers (useful for testing)."""
    _game_loggers.clear()
