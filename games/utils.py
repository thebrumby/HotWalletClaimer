"""
Utility module for security and code quality improvements.
Enhances the main claimer classes with better validation, error handling, and type safety.
"""

import os
import re
import json
from typing import Optional, Dict, Any


class SecurityUtils:
    """Security-related utilities for input validation and sanitization."""

    @staticmethod
    def sanitize_wallet_id(wallet_id: str) -> str:
        """
        Sanitize wallet ID to prevent path traversal and special character issues.

        Args:
            wallet_id: Raw wallet ID input

        Returns:
            Sanitized wallet ID safe for file path use
        """
        if not wallet_id:
            return "Wallet1"

        # Remove path traversal characters and special characters that could cause issues
        sanitized = re.sub(r'[\\/:*?"<>|]', '', wallet_id)
        sanitized = re.sub(r'\s+', '', sanitized)  # Remove whitespace
        sanitized = sanitized.strip()

        # Ensure it has a minimum length
        sanitized = sanitized if sanitized else "Wallet1"

        return sanitized

    @staticmethod
    def validate_phone_number(phone: str) -> bool:
        """
        Validate international phone number format.

        Args:
            phone: Phone number string

        Returns:
            True if valid, False otherwise
        """
        pattern = re.compile(r"^[1-9][0-9]{6,14}$")
        return bool(pattern.match(phone))

    @staticmethod
    def validate_seed_phrase(seed_phrase: str) -> bool:
        """
        Validate seed phrase format (must have exactly 12 words).

        Args:
            seed_phrase: Seed phrase string

        Returns:
            True if valid, False otherwise
        """
        words = seed_phrase.split()
        return len(words) == 12

    @staticmethod
    def secure_path(path: str) -> str:
        """
        Create a secure, normalized file path.

        Resolves '..' and handles path manipulation attempts.

        Args:
            path: Raw file path

        Returns:
            Secure, absolute file path
        """
        return os.path.abspath(os.path.normpath(path))


class Constants:
    """Timeout and configuration constants for the claimer system."""

    # Selenium timeout constants (in seconds)
    DEFAULT_TIMEOUT = 30
    QR_CODE_TIMEOUT = 30
    OTP_TIMEOUT = 20
    2FA_TIMEOUT = 30
    STORAGE_OFFLINE_TIMEOUT = 10
    ELEMENT_CLICK_TIMEOUT = 10
    IMPLICIT_WAIT = 5
    PAGE_LOAD_TIMEOUT = 30

    # File path constants
    DEFAULT_SETTINGS_FILE = "variables.txt"
    STATUS_FILE_PATH = "status.txt"
    SESSION_PATH_PREFIX = "./selenium/"
    SCREENSHOTS_PATH_PREFIX = "./screenshots/"
    BACKUP_PATH_PREFIX = "./backups/"

    # Cache constants
    CACHE_MAX_SIZE_GB = 1
    CACHE_MAX_SESSIONS = 5

    # Telegram API constants
    TELEGRAM_API_TIMEOUT = 5
    MAX_RETRY_ATTEMPTS = 3

    # Session management constants
    SESSION_EXPIRY_SECONDS = 300  # 5 minutes
    SESSION_RETRY_INTERVAL_MIN = 5
    SESSION_RETRY_INTERVAL_MAX = 15


class ErrorHandlingUtils:
    """Utilities for robust error handling."""

    @staticmethod
    def safe_json_load(file_path: str, default_value: Optional[Dict] = None) -> Dict:
        """
        Safely load JSON file with error handling.

        Args:
            file_path: Path to JSON file
            default_value: Value to return if file doesn't exist or is corrupted

        Returns:
            Loaded JSON as dictionary or default value
        """
        if default_value is None:
            default_value = {}

        try:
            if not os.path.exists(file_path):
                return default_value.copy()

            with open(file_path, "r") as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError) as e:
            print(f"Warning: Error loading {file_path}: {e}. Using defaults.")
            return default_value.copy()

    @staticmethod
    def safe_json_save(file_path: str, data: Dict) -> bool:
        """
        Safely save dictionary to JSON file with error handling.

        Args:
            file_path: Path to save JSON file
            data: Dictionary to save

        Returns:
            True if successful, False otherwise
        """
        try:
            with open(file_path, "w") as f:
                json.dump(data, f, indent=2)
            return True
        except IOError as e:
            print(f"Warning: Error saving {file_path}: {e}")
            return False

    @staticmethod
    def validate_integer_input(
        user_input: str,
        min_value: int,
        max_value: int,
        context: str = "value"
    ) -> Optional[int]:
        """
        Validate and parse integer user input.

        Args:
            user_input: User's input string
            min_value: Minimum acceptable value
            max_value: Maximum acceptable value
            context: Description of what is being validated

        Returns:
            Validated integer or None if invalid
        """
        try:
            value = int(user_input)
            if min_value <= value <= max_value:
                return value
            else:
                print(f"Invalid {context}. Must be between {min_value} and {max_value}.")
                return None
        except ValueError:
            print(f"Invalid {context}. Must be a number.")
            return None


class LoggingUtils:
    """Utilities for improved logging and debugging."""

    @staticmethod
    def format_message(message: str, level: int = 2) -> str:
        """
        Format message with optional timestamp.

        Args:
            message: Message to format
            level: Verbosity level

        Returns:
            Formatted message string
        """
        timestamp = datetime.now().strftime("%H:%M:%S")
        return f"[{timestamp}] {message}"

    @staticmethod
    def get_timestamp() -> str:
        """
        Get current timestamp string.

        Returns:
            Current timestamp
        """
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")
