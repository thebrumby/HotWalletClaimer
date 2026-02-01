"""
Centralized logging system for HotWalletClaimer.

This module provides a unified logging interface for all game scripts,
ensuring consistent output levels, log files, and formatting.
"""

import logging
from pathlib import Path
from datetime import datetime
from typing import Optional


class GameLogger:
    """
    Centralized logger for HotWalletClaimer game scripts.

    Provides:
    - File logging with timestamps
    - Console logging controlled by verbose level
    - Multiple log levels (DEBUG, INFO, WARNING, ERROR, CRITICAL)
    - Thread-safe operations

    Example:
        >>> logger = GameLogger("XNode", verbose_level=2)
        >>> logger.info("Starting claim process")
        >>> logger.debug("Element found: #button-claim")
    """

    _instances = {}

    def __new__(cls, name: str, verbose_level: int = 2):
        """
        Create or return existing logger instance.

        Args:
            name: Logger name (typically __name__ or game name)
            verbose_level: Output verbosity (1=minimal, 2=standard, 3=debug)

        Returns:
            GameLogger instance (singleton per name)
        """
        if name not in cls._instances:
            instance = super().__new__(cls)
            instance._initialized = False
            cls._instances[name] = instance
        return cls._instances[name]

    def __init__(self, name: str, verbose_level: int = 2):
        """
        Initialize the logger.

        Args:
            name: Logger name
            verbose_level: 1=warning, 2=info, 3=debug

        Raises:
            ValueError: If verbose_level is invalid
        """
        if self._initialized:
            return

        if verbose_level not in (1, 2, 3):
            raise ValueError("verbose_level must be 1 (warning), 2 (info), or 3 (debug)")

        self.logger = logging.getLogger(name)
        self.logger.setLevel(logging.DEBUG)

        # Ensure logger doesn't propagate to root (prevents duplicate logs)
        self.logger.propagate = False

        # Create logs directory if it doesn't exist
        log_dir = Path("logs")
        log_dir.mkdir(parents=True, exist_ok=True)

        # File handler - logs all levels to file
        timestamp = datetime.now().strftime("%Y%m%d")
        log_file = log_dir / f"{name}_{timestamp}.log"
        fh = logging.FileHandler(log_file)
        fh.setLevel(logging.DEBUG)
        fh.setFormatter(
            logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                datefmt='%Y-%m-%d %H:%M:%S'
            )
        )

        # Console handler - based on verbose_level
        ch = logging.StreamHandler()
        verbose_levels = {
            1: logging.WARNING,   # Minimal output
            2: logging.INFO,      # Standard output
            3: logging.DEBUG      # Debug output
        }
        ch.setLevel(verbose_levels[verbose_level])
        ch.setFormatter(
            logging.Formatter(
                '%(levelname)s - %(message)s'
            )
        )

        # Add handlers to logger
        self.logger.addHandler(fh)
        self.logger.addHandler(ch)

        self._initialized = True

    def info(self, msg: str) -> None:
        """
        Log info level message.

        Args:
            msg: Message to log
        """
        self.logger.info(msg)

    def debug(self, msg: str) -> None:
        """
        Log debug level message.

        Args:
            msg: Message to log
        """
        self.logger.debug(msg)

    def warning(self, msg: str) -> None:
        """
        Log warning level message.

        Args:
            msg: Message to log
        """
        self.logger.warning(msg)

    def error(self, msg: str, exc_info: bool = False) -> None:
        """
        Log error level message.

        Args:
            msg: Message to log
            exc_info: Include exception traceback if True
        """
        self.logger.error(msg, exc_info=exc_info)

    def critical(self, msg: str, exc_info: bool = False) -> None:
        """
        Log critical level message.

        Args:
            msg: Message to log
            exc_info: Include exception traceback if True
        """
        self.logger.critical(msg, exc_info=exc_info)

    def get_logger(self) -> logging.Logger:
        """
        Get the underlying Python logger.

        Returns:
            logging.Logger instance
        """
        return self.logger


def get_logger(name: str, verbose_level: int = 2) -> GameLogger:
    """
    Factory function to create or retrieve a logger.

    Args:
        name: Logger name
        verbose_level: Output verbosity

    Returns:
        GameLogger instance
    """
    return GameLogger(name, verbose_level)
