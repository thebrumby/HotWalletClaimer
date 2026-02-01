"""
HotWalletClaimer - Improved Version
Security enhancements, error handling improvements, and code quality upgrades.
"""

import os
import shutil
import sys
import time
import re
import json
import getpass
import random
import subprocess
from datetime import datetime, timedelta
from typing import Optional, Tuple, Dict, Any, List

# Timeout constants - configurable and well-documented
DEFAULT_TIMEOUT = 30
QR_CODE_TIMEOUT = 30
OTP_TIMEOUT = 20
FLOOD_WAIT_TIMEOUT = 15
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

# Telegram timeout constants
TELEGRAM_API_TIMEOUT = 5
MAX_RETRY_ATTEMPTS = 3

try:
    import fcntl
    from fcntl import flock, LOCK_EX, LOCK_UN, LOCK_NB
    FLOCK_AVAILABLE = True
except ImportError:
    FLOCK_AVAILABLE = False
    flock = None
    LOCK_EX = None
    LOCK_UN = None
    LOCK_NB = None

from selenium import webdriver
from selenium.webdriver import ActionChains
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.keys import Keys
from selenium.common.exceptions import (
    NoSuchElementException,
    TimeoutException,
    StaleElementReferenceException,
    ElementClickInterceptedException,
    UnexpectedAlertPresentException,
    MoveTargetOutOfBoundsException
)
from selenium.webdriver.chrome.service import Service as ChromeService
import requests


class Claimer:
    """
    Base class for all Telegram game claimers.
    Provides common functionality for logging in, session management, and automation.
    """

    def __init__(self):
        self.initialize_settings()
        self.load_settings()
        self.random_offset = random.randint(self.settings['lowestClaimOffset'], self.settings['highestClaimOffset'])
        print(f"Initialising the {self.prefix} Wallet Auto-claim Python Script - Good Luck!")

        self.imported_seedphrase = None

        # Update the settings based on user input
        if len(sys.argv) > 1:
            user_input = sys.argv[1]  # Get session ID from command-line argument
            self.wallet_id = self._sanitize_wallet_id(user_input)
            self.output(f"Session ID provided: {self.wallet_id}", 2)

            # Safely check for a second argument
            if len(sys.argv) > 2 and sys.argv[2] == "reset":
                self.settings['forceNewSession'] = True

            # Check for the --seed-phrase flag and validate it
            if '--seed-phrase' in sys.argv:
                seed_index = sys.argv.index('--seed-phrase') + 1
                if seed_index < len(sys.argv):
                    self.seed_phrase = ' '.join(sys.argv[seed_index:])
                    seed_words = self.seed_phrase.split()
                    if len(seed_words) == 12:
                        self.output(f"Seed phrase accepted:", 2)
                        self.imported_seedphrase = self.seed_phrase
                    else:
                        self.output("Invalid seed phrase. Must have exactly 12 words.", 2)
                else:
                    self.output("No seed phrase provided after --seed-phrase flag. Ignoring.", 2)
        else:
            self.output("\nCurrent settings:", 1)
            for key, value in self.settings.items():
                self.output(f"{key}: {value}", 1)
            user_input = input("\nShould we update our settings? (Default:<enter> / Yes = y): ").strip().lower()
            if user_input == "y":
                self.update_settings()
            user_input = self.get_session_id()
            self.wallet_id = self._sanitize_wallet_id(user_input)

        # Initialize secure paths
        self.session_path = self._secure_path(f"{SESSION_PATH_PREFIX}{self.wallet_id}")
        self.screenshots_path = self._secure_path(f"{SCREENSHOTS_PATH_PREFIX}{self.wallet_id}")
        self.backup_path = self._secure_path(f"{BACKUP_PATH_PREFIX}{self.wallet_id}")

        os.makedirs(self.session_path, exist_ok=True)
        os.makedirs(self.screenshots_path, exist_ok=True)
        os.makedirs(self.backup_path, exist_ok=True)
        self.step = "01"

        # Define our base path for debugging screenshots
        self.screenshot_base = os.path.join(self.screenshots_path, "screenshot")

        if self.settings["useProxy"] and self.settings["proxyAddress"] == "http://127.0.0.1:8080":
            self.run_http_proxy()
        elif self.forceLocalProxy:
            self.run_http_proxy()
            self.output("Use of the built-in proxy is forced on for this game.", 2)
        else:
            self.output("Proxy disabled in settings.", 2)

    def initialize_settings(self) -> None:
        """Initialize default settings for the claimer."""
        self.settings_file = DEFAULT_SETTINGS_FILE
        self.status_file_path = STATUS_FILE_PATH
        self.start_app_xpath = None
        self.settings = {}
        self.driver = None
        self.target_element = None
        self.random_offset = 0
        self.seed_phrase = None
        self.wallet_id = ""
        self.script = "default_script.py"
        self.prefix = "Default:"
        self.allow_early_claim = True
        self.default_platform = "web"
        self.forceLocalProxy = False
        self.forceRequestUserAgent = False
        self.url = ""

    @staticmethod
    def _sanitize_wallet_id(wallet_id: str) -> str:
        """
        Sanitize wallet ID to prevent path traversal and special character issues.

        Removes any characters that could be used for path traversal or injection.

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
    def _secure_path(path: str) -> str:
        """
        Create a secure, normalized file path.

        Resolves '..' and handles path manipulation attempts.

        Args:
            path: Raw file path

        Returns:
            Secure, absolute file path
        """
        return os.path.abspath(os.path.normpath(path))

    def load_settings(self) -> None:
        """Load settings from file or create defaults."""
        default_settings = {
            "forceClaim": False,
            "debugIsOn": True,
            "hideSensitiveInput": True,
            "screenshotQRCode": True,
            "maxSessions": 1,
            "verboseLevel": 2,
            "telegramVerboseLevel": 0,
            "lowestClaimOffset": 0,
            "highestClaimOffset": 15,
            "forceNewSession": False,
            "useProxy": False,
            "proxyAddress": "http://127.0.0.1:8080",
            "requestUserAgent": False,
            "telegramBotToken": "",
            "telegramBotChatId": "",
            "enableCache": True
        }

        if os.path.exists(self.settings_file):
            try:
                with open(self.settings_file, "r") as f:
                    loaded_settings = json.load(f)
                # Filter out unused settings from previous versions
                self.settings = {k: loaded_settings.get(k, v) for k, v in default_settings.items()}
                self.output("Settings loaded successfully.", 3)
            except json.JSONDecodeError as e:
                self.output(f"Error loading settings file: {e}. Using defaults.", 1)
                self.settings = default_settings.copy()
        else:
            self.settings = default_settings.copy()
            self.save_settings()

    def save_settings(self) -> None:
        """Save current settings to file."""
        try:
            with open(self.settings_file, "w") as f:
                json.dump(self.settings, f, indent=2)
            self.output("Settings saved successfully.", 3)
        except Exception as e:
            self.output(f"Error saving settings: {e}", 1)

    def output(self, string: str, level: int = 2) -> None:
        """
        Output message with configurable verbosity level.
        Also forwards to Telegram bot if configured.

        Args:
            string: Message to output
            level: Verbosity level (1=minimal, 2=claim steps, 3=all messages)
        """
        if self.settings['verboseLevel'] >= level:
            print(string)
        if self.settings['telegramBotToken'] and not self.settings['telegramBotChatId']:
            try:
                self.settings['telegramBotChatId'] = self.get_telegram_bot_chat_id()
                self.save_settings()
            except ValueError as e:
                pass
        if self.settings['telegramBotChatId'] and self.wallet_id and self.settings['telegramVerboseLevel'] >= level:
            self.send_message(string)

    def get_telegram_bot_chat_id(self) -> str:
        """
        Fetches the most recent update and returns its chat_id and message_id.

        Returns:
            Chat ID from the latest Telegram update

        Raises:
            ValueError: If no updates found or no message object in update
        """
        url = f"https://api.telegram.org/bot{self.settings['telegramBotToken']}/getUpdates"
        params = {
            "limit": 1,
            "timeout": 0,
        }
        try:
            response = requests.get(url, params=params, timeout=TELEGRAM_API_TIMEOUT)
            response.raise_for_status()
            data = response.json()
        except requests.RequestException as e:
            raise ValueError(f"Failed to fetch Telegram updates: {e}")

        updates = data.get("result", [])
        if not updates:
            raise ValueError("No updates found. Ensure the bot has received at least one message.")

        latest = updates[-1]
        msg = latest.get("message") or latest.get("edited_message")
        if not msg:
            raise ValueError("Latest update contains no message object.")

        return str(msg["chat"]["id"])

    def send_message(self, string: str) -> None:
        """
        Send message via Telegram bot.

        Args:
            string: Message to send
        """
        try:
            if self.settings['telegramBotChatId'] == "":
                self.settings['telegramBotChatId'] = self.get_telegram_bot_chat_id()

            message = f"{self.wallet_id}: {string}"
            url = f"https://api.telegram.org/bot{self.settings['telegramBotToken']}/sendMessage?chat_id={self.settings['telegramBotChatId']}&text={message}"
            response = requests.get(url, timeout=TELEGRAM_API_TIMEOUT).json()

            if not response.get("ok"):
                raise ValueError(f"Failed to send message: {response}")
        except ValueError as e:
            self.output(f"Error sending Telegram message: {e}", 3)

    def get_session_id(self) -> str:
        """
        Prompts the user for a session ID or determines the next sequential ID.

        Returns:
            Session ID string
        """
        self.output(f"Your session will be prefixed with: {self.prefix}", 1)
        user_input = input("Enter your unique Session Name here, or hit <enter> for the next sequential wallet: ").strip()

        if not user_input:
            user_input = f"Wallet1"

        return self.prefix + user_input

    def setup_driver(self) -> webdriver.Chrome:
        """
        Configure and initialize the Chrome WebDriver with security options.

        Returns:
            Configured Chrome WebDriver instance

        Raises:
            Exception: If ChromeDriver setup fails
        """
        chrome_options = Options()
        chrome_options.add_argument(f"user-data-dir={self.session_path}")
        chrome_options.add_argument("--profile-directory=Default")
        chrome_options.add_argument("--headless=new")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--enable-features=NetworkService,NetworkServiceInProcess")
        chrome_options.add_argument("--disable-background-networking")
        chrome_options.add_argument("--enable-automation")

        # User agent detection
        try:
            cookies_path = f"{self.session_path}/cookies.json"
            if os.path.exists(cookies_path):
                with open(cookies_path, "r") as file:
                    cookies = json.load(file)
                    user_agent_cookie = next((cookie for cookie in cookies if cookie["name"] == "user_agent"), None)
                    if user_agent_cookie and user_agent_cookie["value"]:
                        user_agent = user_agent_cookie["value"]
                        self.output(f"Using saved user agent: {user_agent}", 2)
                    else:
                        user_agent = "Mozilla/5.0 (iPhone; CPU iPhone OS 17_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) EdgiOS/124.0.2478.50 Version/17.0 Mobile/15E148 Safari/604.1"
                        self.output("No user agent found, using default.", 2)
            else:
                user_agent = "Mozilla/5.0 (iPhone; CPU iPhone OS 17_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) EdgiOS/124.0.2478.50 Version/17.0 Mobile/15E148 Safari/604.1"
                self.output("Cookies file not found, using default user agent.", 2)
        except (FileNotFoundError, json.JSONDecodeError) as e:
            self.output(f"Error loading user agent: {e}", 3)
            user_agent = "Mozilla/5.0 (iPhone; CPU iPhone OS 17_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) EdgiOS/124.0.2478.50 Version/17.0 Mobile/15E148 Safari/604.1"

        # Adjust platform based on user agent
        if any(keyword in user_agent for keyword in ['iPhone', 'iPad', 'iOS', 'iPhone OS']):
            self.default_platform = "ios"
            self.output("Detected iOS platform from user agent. tgWebAppPlatform will be changed to 'ios' later.", 2)
        elif 'Android' in user_agent:
            self.default_platform = "android"
            self.output("Detected Android platform from user agent. Set tgWebAppPlatform to 'android'.", 2)
        else:
            self.default_platform = "web"
            self.output("Default platform set to 'web'.", 3)

        chrome_options.add_argument(f"user-agent={user_agent}")
        chrome_options.add_argument("--disable-blink-features=AutomationControlled")
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option('useAutomationExtension', False)

        if not self.settings.get("enableCache", True) and int(self.step) >= 100:
            chrome_options.add_argument("--disable-application-cache")

        if self.settings["useProxy"] or self.forceLocalProxy:
            proxy_server = self.settings["proxyAddress"]
            chrome_options.add_argument(f"--proxy-server={proxy_server}")

        chrome_options.add_argument("--ignore-certificate-errors")
        chrome_options.add_argument("--allow-running-insecure-content")
        chrome_options.add_argument("--test-type")

        chromedriver_path = shutil.which("chromedriver")
        if chromedriver_path is None:
            self.output("ChromeDriver not found in PATH. Please ensure it is installed.", 1)
            raise Exception("ChromeDriver not found")

        try:
            service = Service(chromedriver_path)
            self.driver = webdriver.Chrome(service=service, options=chrome_options)
            return self.driver
        except Exception as e:
            self.output(f"Initial ChromeDriver setup may have failed: {e}", 1)
            self.output("Please ensure you have the correct ChromeDriver version for your system.", 1)
            raise

    def get_driver(self) -> webdriver.Chrome:
        """
        Get or create the WebDriver instance.

        Returns:
            Chrome WebDriver instance
        """
        if self.driver is None:
            self.manage_session()
            self.driver = self.setup_driver()
            self.output("\nCHROME DRIVER INITIALISED: Try not to exit the script before it detaches.", 2)
        return self.driver

    def quit_driver(self) -> None:
        """
        Quit the WebDriver and release the session.
        """
        if self.driver:
            self.driver.quit()
            self.output("\nCHROME DRIVER DETACHED: It is now safe to exit the script.", 2)
            self.driver = None
            self.release_session()

    def manage_session(self) -> None:
        """
        Manage session coordination using file locking.
        Ensures only maxSessions concurrent sessions are active.
        """
        current_session = self.session_path
        current_timestamp = int(time.time())
        session_started = False
        new_message = True
        output_priority = 2

        while True:
            try:
                # Create status file if it doesn't exist
                if not os.path.exists(self.status_file_path):
                    with open(self.status_file_path, "w") as file:
                        json.dump({}, file)

                with open(self.status_file_path, "r+") as file:
                    if FLOCK_AVAILABLE:
                        flock(file, LOCK_EX)

                    try:
                        status = json.load(file)

                        # Clean up expired sessions (> 5 minutes old)
                        expired_sessions = [
                            sid for sid, ts in list(status.items())
                            if current_timestamp - ts > 300
                        ]
                        for sid in expired_sessions:
                            del status[sid]
                            self.output(f"Removed expired session: {sid}", 3)

                        # Check for available slots
                        active_sessions = {
                            k: v for k, v in status.items()
                            if k != current_session
                        }

                        if len(active_sessions) < self.settings['maxSessions']:
                            status[current_session] = current_timestamp
                            file.seek(0)
                            json.dump(status, file)
                            file.truncate()
                            self.output(f"Session started: {current_session}", 3)
                            session_started = True
                            break

                    except json.JSONDecodeError as e:
                        self.output(f"Corrupted status file, resetting: {e}", 3)
                        with open(self.status_file_path, "w") as file:
                            json.dump({}, file)
                        status = {}
                        status[current_session] = current_timestamp
                        file.seek(0)
                        json.dump(status, file)
                        file.truncate()
                        session_started = True
                        break
                    finally:
                        if FLOCK_AVAILABLE:
                            flock(file, LOCK_UN)

                if not session_started:
                    self.output(
                        f"Waiting for slot. Current sessions: {len(active_sessions)}/{self.settings['maxSessions']}",
                        output_priority
                    )
                    if new_message:
                        new_message = False
                        output_priority = 3
                    time.sleep(random.randint(5, 15))
                else:
                    break

            except Exception as e:
                self.output(f"Error managing session: {e}", 1)
                break

    def release_session(self) -> None:
        """
        Release the current session by removing it from the status file.
        """
        current_session = self.session_path

        if not os.path.exists(self.status_file_path):
            return

        try:
            with open(self.status_file_path, "r+") as file:
                if FLOCK_AVAILABLE:
                    flock(file, LOCK_EX)

                try:
                    status = json.load(file)
                    if current_session in status:
                        del status[current_session]
                        file.seek(0)
                        json.dump(status, file)
                        file.truncate()
                    self.output(f"Session released: {current_session}", 3)
                finally:
                    if FLOCK_AVAILABLE:
                        flock(file, LOCK_UN)
        except Exception as e:
            self.output(f"Error releasing session: {e}", 3)

    # Abstract methods that must be implemented by subclasses
    def next_steps(self) -> None:
        """Execute next steps - must be overridden by subclass."""
        self.output("Function 'next_steps' - Not defined (Need override in child class)", 1)

    def full_claim(self) -> int:
        """
        Execute the full claim process and return wait time for next claim.

        Returns:
            Wait time in minutes until next claim should be attempted
        """
        self.output("Function 'full_claim' - Not defined (Need override in child class)", 1)
        return 30

    def launch_iframe(self) -> None:
        """Launch the game iframe - must be overridden by subclass."""
        self.output("Function 'launch_iframe' - Not defined (Need override in child class)", 1)

    def log_into_telegram(self, user_input: Optional[str] = None) -> None:
        """
        Log into Telegram using QR code or OTP method.

        Args:
            user_input: Optional wallet/session ID
        """
        self.step = "01"
        self.session_path = f"{SESSION_PATH_PREFIX}{user_input}" if user_input else self.session_path

        # Recreate directories if needed
        if os.path.exists(self.session_path):
            shutil.rmtree(self.session_path)
        os.makedirs(self.session_path, exist_ok=True)

        self.screenshots_path = self._secure_path(f"{SCREENSHOTS_PATH_PREFIX}{user_input}")
        if os.path.exists(self.screenshots_path):
            shutil.rmtree(self.screenshots_path)
        os.makedirs(self.screenshots_path, exist_ok=True)

        self.backup_path = self._secure_path(f"{BACKUP_PATH_PREFIX}{user_input}")
        if os.path.exists(self.backup_path):
            shutil.rmtree(self.backup_path)
        os.makedirs(self.backup_path, exist_ok=True)

        self.driver = self.get_driver()

        # QR Code Method
        if self.settings['screenshotQRCode']:
            self._login_with_qr_code()

        # OTP Login Method
        self.increase_step()
        self.output(f"Step {self.step} - Initiating the One-Time Password (OTP) method...\n", 1)
        self.driver.get(self.url)
        xpath = "//button[contains(@class, 'btn-primary') and contains(., 'Log in by phone Number')]"
        self.move_and_click(xpath, 30, True, "switch to log in by phone number", self.step, "visible")
        self.increase_step()

        # Country Code Selection
        xpath = "//div[contains(@class, 'input-field-input')]"
        self.target_element = self.move_and_click(xpath, 30, True, "update user's country", self.step, "visible")
        if not self.target_element:
            self.output(f"Step {self.step} - Failed to find country input field.", 1)
            return

        user_input_country = input(f"Step {self.step} - Please enter your Country Name as it appears in the Telegram list: ").strip()
        self.target_element.send_keys(user_input_country)
        self.target_element.send_keys(Keys.RETURN)
        self.increase_step()

        # Phone Number Input
        xpath = "//div[contains(@class, 'input-field-input') and @inputmode='decimal']"
        self.target_element = self.move_and_click(xpath, 30, True, "request user's phone number", self.step, "visible")
        if not self.target_element:
            self.output(f"Step {self.step} - Failed to find phone number input field.", 1)
            return

        user_phone = self._get_phone_number()
        self.target_element.send_keys(user_phone)
        self.increase_step()

        # Wait for the "Next" button
        xpath = "//button//span[contains(text(), 'Next')]"
        self.move_and_click(xpath, 15, True, "click next to proceed to OTP entry", self.step, "visible")
        self.increase_step()

        # OTP Entry
        try:
            wait = WebDriverWait(self.driver, OTP_TIMEOUT)
            if self.settings['debugIsOn']:
                self.debug_information("preparing for TG OTP", "check")
            otp_element = wait.until(EC.visibility_of_element_located((By.XPATH, "//input[@type='tel']")))
            otp = input(f"Step {self.step} - What is the Telegram OTP from your app? ")
            otp_element.click()
            otp_element.send_keys(otp)
            self.output(f"Step {self.step} - Let's try to log in using your Telegram OTP.\n", 3)
            self.increase_step()
        except TimeoutException:
            self.output(f"Step {self.step} - OTP input field not found within {OTP_TIMEOUT} seconds.", 1)
        except Exception as e:
            self.output(f"Step {self.step} - Login failed. Error: {e}", 1)
            if self.settings['debugIsOn']:
                self.debug_information("telegram login failed", "error")

        self.increase_step()
        self.test_for_2fa()

        if self.settings['debugIsOn']:
            self.debug_information("telegram OTP successfully entered", "check")

    def _get_phone_number(self) -> str:
        """
        Get and validate phone number from user.

        Returns:
            Validated phone number string
        """
        while True:
            if self.settings['hideSensitiveInput']:
                user_phone = getpass.getpass(f"Step {self.step} - Please enter your phone number without leading 0 (hidden input): ")
            else:
                user_phone = input(f"Step {self.step} - Please enter your phone number without leading 0 (visible input): ")

            if self._validate_phone_number(user_phone):
                self.output(f"Step {self.step} - Valid phone number entered.", 3)
                return user_phone
            else:
                self.output(f"Step {self.step} - Invalid phone number. Must be 7 to 15 digits and without leading 0.", 1)

    @staticmethod
    def _validate_phone_number(phone: str) -> bool:
        """
        Validate international phone number format.

        Args:
            phone: Phone number string

        Returns:
            True if valid, False otherwise
        """
        pattern = re.compile(r"^[1-9][0-9]{6,14}$")
        return bool(pattern.match(phone))

    def test_for_2fa(self) -> None:
        """
        Test for and handle two-factor authentication if required.
        """
        try:
            self.increase_step()
            WebDriverWait(self.driver, 2FA_TIMEOUT).until(
                lambda d: d.execute_script('return document.readyState') == 'complete'
            )
            xpath = "//input[@type='password' and contains(@class, 'input-field-input')]"
            fa_input = self.move_and_click(xpath, 15, False, "check for 2FA requirement", self.step, "present")

            if fa_input:
                if self.settings['hideSensitiveInput']:
                    tg_password = getpass.getpass(f"Step {self.step} - Enter your Telegram 2FA password: ")
                else:
                    tg_password = input(f"Step {self.step} - Enter your Telegram 2FA password: ")
                fa_input.send_keys(tg_password + Keys.RETURN)
                self.output(f"Step {self.step} - 2FA password sent.\n", 3)
                self.output(f"Step {self.step} - Checking if the 2FA password is correct.\n", 2)

                xpath = "//*[contains(text(), 'Incorrect password')]"
                try:
                    incorrect_password = WebDriverWait(self.driver, 8).until(
                        EC.visibility_of_element_located((By.XPATH, xpath))
                    )
                    self.output(f"Step {self.step} - 2FA password is marked as incorrect.", 1)
                    if self.settings['debugIsOn']:
                        self.debug_information("incorrect telegram 2FA entered", "error")
                    self.quit_driver()
                    sys.exit()
                except TimeoutException:
                    pass

                self.output(f"Step {self.step} - No password error found.", 3)
                xpath = "//input[@type='password' and contains(@class, 'input-field-input')]"
                fa_input = self.move_and_click(xpath, 5, False, "final 2FA check", self.step, "present")
                if fa_input:
                    self.output(f"Step {self.step} - 2FA password entry is still showing.", 1)
                    sys.exit()
                self.output(f"Step {self.step} - 2FA password check passed.", 3)
            else:
                self.output(f"Step {self.step} - Two-factor Authorization not required.\n", 3)

        except TimeoutException:
            self.output(f"Step {self.step} - Two-factor Authorization not required.\n", 3)
        except Exception as e:
            self.output(f"Step {self.step} - Login failed during 2FA: {e}", 1)
            if self.settings['debugIsOn']:
                self.debug_information("unspecified error during telegram 2FA", "error")

    def increase_step(self) -> None:
        """Increment the current step counter."""
        step_int = int(self.step) + 1
        self.step = f"{step_int:02}"

    def replace_platform(self) -> None:
        """
        Replace platform in iframe URL for proper mobile/web emulation.
        """
        self.output(f"Step {self.step} - Attempting to replace platform in iframe URL if necessary...", 2)
        try:
            wait = WebDriverWait(self.driver, PAGE_LOAD_TIMEOUT)
            container = wait.until(EC.presence_of_element_located((By.CLASS_NAME, 'web-app-body')))
            iframe = container.find_element(By.TAG_NAME, "iframe")
            iframe_url = iframe.get_attribute("src")

            if "tgWebAppPlatform=web" in iframe_url:
                iframe_url = iframe_url.replace("tgWebAppPlatform=web", f"tgWebAppPlatform={self.default_platform}")
                self.output(f"Step {self.step} - Platform 'web' found and replaced with '{self.default_platform}'.", 2)
                self.driver.execute_script("arguments[0].src = arguments[1];", iframe, iframe_url)
            else:
                self.output("Step {self.step} - No 'tgWebAppPlatform=web' parameter found in iframe URL.", 2)
        except TimeoutException:
            self.output(f"Step {self.step} - Failed to locate iframe within {PAGE_LOAD_TIMEOUT} seconds.", 3)
        except Exception as e:
            self.output(f"Step {self.step} - Error modifying iframe URL: {e}", 3)
        finally:
            self.increase_step()
            time.sleep(5)

    def move_and_click(
        self,
        xpath: str,
        timeout: int = ELEMENT_CLICK_TIMEOUT,
        should_click: bool = True,
        reason: str = "",
        step: str = "",
        condition: str = "visible"
    ) -> Optional[Any]:
        """
        Move to and click on an element with retry logic.

        Args:
            xpath: XPath selector for the element
            timeout: Maximum time to wait for element
            should_click: Whether to click the element
            reason: Description of what the click is for
            step: Current step number
            condition: Expected condition (visible/present/clickable)

        Returns:
            Element if found and clicked, None otherwise
        """
        try:
            wait = WebDriverWait(self.driver, timeout)
            element = wait.until(
                EC.presence_of_element_located((By.XPATH, xpath))
            )

            if condition == "present" or condition == "visible":
                wait.until(
                    lambda d: element.is_displayed() or condition == "present"
                )

            if should_click:
                try:
                    self.driver.execute_script(
                        "arguments[0].scrollIntoView({block:'center', inline:'center'});", element
                    )
                    ActionChains(self.driver).move_to_element(element).pause(0.05).click(element).perform()
                except Exception:
                    self.driver.execute_script("arguments[0].click();", element)

            if reason and self.settings['verboseLevel'] >= 2:
                self.output(f"Step {step} - {reason} ({condition})", 3)

            return element

        except TimeoutException:
            if self.settings['verboseLevel'] >= 1:
                self.output(f"Step {step} - Element '{xpath}' not found within {timeout} seconds.", 1)
        except Exception as e:
            if self.settings['verboseLevel'] >= 1:
                self.output(f"Step {step} - Error interacting with element: {e}", 1)

        return None

    def debug_information(self, note: str, status: str) -> None:
        """
        Save debug information as screenshot.

        Args:
            note: Description of the debug event
            status: Status of the debug event (check/error)
        """
        if self.settings['debugIsOn'] and self.driver:
            try:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                screenshot_path = os.path.join(self.screenshots_path, f"{note}_{timestamp}.png")
                self.driver.save_screenshot(screenshot_path)
            except Exception as e:
                self.output(f"Error saving screenshot: {e}", 3)

    def _in_game_dom(self) -> bool:
        """
        Check if currently in game DOM.

        Returns:
            True if in game DOM, False otherwise
        """
        try:
            if self.driver.find_elements(By.XPATH, "//div[contains(@class,'Upgrader')]"):
                return True
            if self.driver.find_elements(By.XPATH, "//div[contains(@class,'UpgradesPage')]"):
                return True
            return False
        except Exception:
            return False

    def strip_html_and_non_numeric(self, element: Any) -> Optional[str]:
        """
        Extract numeric value from HTML element.

        Args:
            element: Selenium WebElement

        Returns:
            Numeric string or None
        """
        try:
            text = element.text or self.driver.execute_script("return arguments[0].textContent;", element) or ""
            return self.strip_non_numeric(text)
        except Exception:
            return None

    def strip_non_numeric(self, text: str) -> Optional[str]:
        """
        Remove non-numeric characters from text.

        Args:
            text: Input string

        Returns:
            Numeric string or None
        """
        if not text:
            return None
        return re.sub(r'[^0-9.-]', '', text).strip()


def main():
    """Main entry point for the claimer."""
    claimer = Claimer()
    claimer.run()


if __name__ == "__main__":
    main()
