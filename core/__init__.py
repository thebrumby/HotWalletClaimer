"""
Core modules for HotWalletClaimer.

This package contains the central logging system and shared functionality.
"""

from .logger import GameLogger, get_logger

__all__ = ['GameLogger', 'get_logger']
