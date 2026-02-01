"""
Automate HOT (HereWallet) game claims and storage management.

This class handles:
- Telegram authentication
- HOT wallet creation/import
- Storage widget management
- Daily reward claiming
- Near balance monitoring

Configuration:
    Settings are loaded from variables.txt.
    XPaths are loaded from config/selectors/hot.json

Example:
    >>> claimer = HotClaimer()
    >>> claimer.run()
"""

import os
import shutil
import sys
import time
import re
import json
import random
import subprocess
from pathlib import Path
from PIL import Image
from pyzbar.pyzbar import decode
import qrcode_terminal
import fcntl
from fcntl import flock, LOCK_EX, LOCK_UN, LOCK_NB
from selenium import webdriver
from selenium.webdriver import ActionChains
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.keys import Keys
from selenium.common.exceptions import NoSuchElementException, TimeoutException, StaleElementReferenceException, ElementClickInterceptedException
from datetime import datetime, timedelta
from selenium.webdriver.chrome.service import Service as ChromeService

from claimer import Claimer
from core.logger import GameLogger
from config.selectors import load_selectors


class HotClaimer(Claimer):
    """
    Automate HOT wallet claims and storage management.

    Features:
    - Telegram login with QR code or phone number
    - Hot wallet creation
    - Storage widget management
    - Daily reward claiming
    - Near balance monitoring

    Args:
        Inherits all arguments from Claimer class
    """

    def initialize_settings(self):
        """Initialize game-specific settings."""
        super().initialize_settings()
        self.script = "games/hot.py"
        self.prefix = "HOT:"
        self.url = "https://web.telegram.org/k/#@herewalletbot"
        self.pot_full = "Filled"
        self.pot_filling = "to fill"
        self.seed_phrase = None
        self.forceLocalProxy = False
        self.forceRequestUserAgent = False
        self.step = "01"
        self.imported_seedphrase = None
        self.start_app_xpath = self.selectors['xpaths']['extract']['start_app_button']
        self.start_app_menu_item = self.selectors['xpaths']['extract']['start_app_button']

    def __init__(self):
        """Initialize HotClaimer with logging and selectors."""
        self.logger = GameLogger(__name__, self.settings['verboseLevel'])
        self.settings_file = "variables.txt"
        self.status_file_path = "status.txt"
        self.wallet_id = ""
        self.selectors = load_selectors('hot')
        self.load_settings()
        self.random_offset = random.randint(self.settings['lowestClaimOffset'], self.settings['highestClaimOffset'])
        super().__init__()

    def add_widget_and_open_storage(self) -> bool:
        """
        Add widget and open storage interface.

        Returns:
            bool: True if successful, False otherwise
        """
        try:
            xpath = self.selectors['selectors']['add_widget']
            present = self.move_and_click(
                xpath, 10, False,
                "test if 'Add widget' present (may not be present)",
                self.step, "clickable"
            )
            self.increase_step()

            if not present:
                self.logger.debug(f"Step {self.step} - 'Add widget' not present/visible. Skipping.")
                return False

            self.brute_click(xpath, timeout=15, action_description="click the 'Add widget' icon")
            self.increase_step()

            storage_xpath = self.selectors['selectors']['storage_link']
            self.brute_click(storage_xpath, timeout=15, action_description="click the 'Storage' link (single pass)")
            self.increase_step()

            self.set_cookies()
            return True

        except Exception as e:
            self.logger.error(f"Step {self.step} - Error in Add widget + Storage sequence: {e}", exc_info=True)
            return False

    def next_steps(self) -> None:
        """
        Navigate to the HOT wallet and authenticate.

        Handles:
        - Telegram login (QR or phone number)
        - Hot wallet creation
        - Widget addition
        - Cookie management
        """
        try:
            self.launch_iframe()
            self.increase_step()

            xpath = self.selectors['selectors']['import_account_button']
            self.move_and_click(xpath, 30, True, "find the HereWallet log-in button", "08", "clickable")
            self.increase_step()

            xpath = self.selectors['selectors']['seed_phrase_input']
            self.move_and_click(xpath, 30, True, "find the seed phrase or private key element", "08", "clickable")
            self.increase_step()

            xpath = self.selectors['selectors']['seed_phrase_input']
            input_field = self.move_and_click(xpath, 30, True, "locate seedphrase textbox", self.step, "clickable")
            if not self.imported_seedphrase:
                self.imported_seedphrase = self.validate_seed_phrase()
            input_field.send_keys(self.imported_seedphrase)
            self.logger.info(f"Step {self.step} - Was successfully able to enter the seed phrase...")
            self.increase_step()

            xpath = self.selectors['selectors']['terms_checkbox']
            self.move_and_click(xpath, 30, True, "select the tickbox to agree to the terms", self.step, "clickable")
            self.increase_step()

            xpath = self.selectors['selectors']['continue_button']
            self.move_and_click(xpath, 30, True, "click continue after seedphrase entry", self.step, "clickable")
            self.increase_step()

            self.logger.info(f"Step {self.step} - Attempting to click broken Continue button.")
            self.driver.execute_script("""
                const timeout = 180000; // 180s
                const interval = 300;   // poll every 300ms
                const start = Date.now();

                return new Promise((resolve, reject) => {
                    const timer = setInterval(() => {
                        const btn = [...document.querySelectorAll('button')]
                            .find(b => b.textContent && b.textContent.trim().includes('Continue'));

                        if (btn) {
                            btn.scrollIntoView({ block: 'center', inline: 'center' });
                            btn.click();
                            clearInterval(timer);
                            resolve(true);
                        }

                        if (Date.now() - start > timeout) {
                            clearInterval(timer);
                            reject('Continue button not found within 180s');
                        }
                    }, interval);
                });
            """)
            self.increase_step()

            xpath = self.selectors['selectors']['got_it_button']
            self.move_and_click(xpath, 30, True, "accept new terms & conditions", self.step, "clickable")
            self.increase_step()

            self.add_widget_and_open_storage()
            self.increase_step()

            self.set_cookies()

        except TimeoutException:
            self.logger.error(f"Step {self.step} - Failed to find or switch to the iframe within the timeout period.")
        except Exception as e:
            self.logger.error(f"Step {self.step} - An error occurred: {e}", exc_info=True)

    def full_claim(self) -> int:
        """
        Execute complete claim process with wait time calculation.

        Returns:
            int: Wait time in minutes before next claim
        """
        self.step = "100"
        low_near = True

        self.launch_iframe()

        xpath = self.selectors['selectors']['accept_button']
        self.move_and_click(xpath, 10, True, "accept terms & conditions", self.step, "clickable")
        self.increase_step()

        xpath = self.selectors['selectors']['got_it_button']
        self.move_and_click(xpath, 10, True, "accept the new terms & conditions!", self.step, "clickable")
        self.increase_step()

        xpath = self.selectors['selectors']['near_balance']
        self.move_and_click(xpath, 30, False, "move to the 'Near' balance.", self.step, "visible")
        near = self.monitor_element(xpath, 20, "obtain your 'Near' Balance")
        if near:
            try:
                last_value_float = float(near)
                if last_value_float > 0.2:
                    low_near = False
                    self.logger.debug(f"Step {self.step} - Cleared the low 'Near' balance flag as current balance is: {last_value_float}")
                else:
                    self.logger.debug(f"Step {self.step} - The low 'Near' balance flag reamins in place, as current balance is: {last_value_float}")

            except ValueError:
                self.logger.warning(f"Step {self.step} - Conversion of Near Balance to float failed.")
        else:
            self.logger.debug(f"Step {self.step} - Unable to pull your near balance.")
        self.increase_step()

        self.add_widget_and_open_storage()
        self.increase_step()

        xpath = self.selectors['selectors']['storage_element']
        self.move_and_click(xpath, 30, True, "click the 'storage' link", self.step, "clickable")
        self.increase_step()

        self.get_balance(False)
        self.get_profit_hour(True)

        wait_time_text = self.get_wait_time(self.step, "pre-claim")

        try:
            if wait_time_text != "Filled":
                matches = re.findall(r'(\d+)([hm])', wait_time_text)
                remaining_wait_time = (sum(int(value) * (60 if unit == 'h' else 1) for value, unit in matches))
                if self.settings['lowestClaimOffset'] < 0:
                    threshold = abs(self.settings['lowestClaimOffset'])
                else:
                    threshold = 5
                if remaining_wait_time < threshold or self.settings["forceClaim"]:
                    self.settings['forceClaim'] = True
                    self.logger.debug(f"Step {self.step} - the remaining time to claim is less than the minimum offset, so applying: settings['forceClaim'] = True")
                else:
                    remaining_time = self.apply_random_offset(remaining_wait_time)
                    self.logger.info(f"Step {self.step} - Original wait time {wait_time_text} - {remaining_wait_time} minutes, We'll sleep for {remaining_time} minutes after random offset.")
                    return remaining_time
        except Exception as e:
            self.logger.warning(f"Error encountered: {str(e)}")
            return 120

        if not wait_time_text:
            return 60

        try:
            self.logger.info(f"Step {self.step} - The pre-claim wait time is : {wait_time_text} and random offset is {self.random_offset} minutes.")
            self.increase_step()

            if wait_time_text == "Filled" or self.settings['forceClaim']:
                try:
                    original_window = self.driver.current_window_handle
                    xpath = self.selectors['selectors']['check_news_button']
                    self.move_and_click(xpath, 20, True, "check for NEWS.", self.step, "clickable")
                    self.driver.switch_to.window(original_window)
                except TimeoutException:
                    if self.settings['debugIsOn']:
                        self.logger.debug(f"Step {self.step} - No news to check or button not found.")
                self.increase_step()

                try:
                    self.select_iframe(self.step)
                    self.increase_step()

                    xpath = self.selectors['selectors']['claim_button']
                    self.move_and_click(xpath, 20, True, "click the claim button (1st button)", self.step, "clickable")
                    self.increase_step()

                    self.logger.info(f"Step {self.step} - Let's wait for the pending Claim spinner to stop spinning...")
                    time.sleep(5)
                    wait = WebDriverWait(self.driver, 240)
                    spinner_xpath = self.selectors['selectors']['spinner']
                    try:
                        wait.until(EC.invisibility_of_element_located((By.XPATH, spinner_xpath)))
                        self.logger.debug(f"Step {self.step} - Pending action spinner has stopped.")
                    except TimeoutException:
                        self.logger.warning(f"Step {self.step} - Looks like the site has lag - the Spinner did not disappear in time.")
                    self.increase_step()
                    wait_time_text = self.get_wait_time(self.step, "post-claim")
                    matches = re.findall(r'(\d+)([hm])', wait_time_text)
                    total_wait_time = self.apply_random_offset(sum(int(value) * (60 if unit == 'h' else 1) for value, unit in matches))
                    self.increase_step()

                    self.get_balance(True)

                    if wait_time_text == "Filled":
                        if low_near:
                            self.logger.info(f"Step {self.step} - The wait timer is still showing: Filled.")
                            self.logger.info(f"Step {self.step} - We could not confirm you have >0.2 Near, which may have caused the claim to fail.")
                            self.logger.info(f"Step {self.step} - Kindly check in the GUI if you can claim manually, and consider topping up your NEAR balance.")
                            self.logger.info(f"Step {self.step} - We'll check back in 1 hour to see if the claim processed and if not, try again.")
                        else:
                            self.logger.info(f"Step {self.step} - The wait timer is still showing: Filled - claim failed.")
                            self.logger.info(f"Step {self.step} - This means either the claim failed, or there is >4 minutes lag in the game.")
                            self.logger.info(f"Step {self.step} - We'll check back in 1 hour to see if the claim processed and if not, try again.")
                    else:
                        self.logger.info(f"Step {self.step} - Successful Claim: Next claim {wait_time_text} / {total_wait_time} minutes.")

                    return max(60, total_wait_time)

                except TimeoutException:
                    self.logger.error(f"Step {self.step} - The claim process timed out: Maybe the site has lag? Will retry after one hour.")
                    return 60
                except Exception as e:
                    self.logger.error(f"Step {self.step} - An error occurred while trying to claim: {e}")
                    return 60

            else:
                matches = re.findall(r'(\d+)([hm])', wait_time_text)
                if matches:
                    total_time = sum(int(value) * (60 if unit == 'h' else 1) for value, unit in matches)
                    total_time += 1
                    total_time = max(5, total_time)
                    self.logger.info(f"Step {self.step} - Not Time to claim this wallet yet. Wait for {total_time} minutes until the storage is filled.")
                    return total_time
                else:
                    self.logger.info(f"Step {self.step} - No wait time data found? Let's check again in one hour.")
                    return 60
        except Exception as e:
            self.logger.error(f"Step {self.step} - An unexpected error occurred: {e}", exc_info=True)
            return 60

    def get_balance(self, claimed: bool) -> None:
        """
        Get HOT balance.

        Args:
            claimed: True if this is after claiming
        """
        prefix = "After" if claimed else "Before"
        default_priority = 2 if claimed else 3
        priority = max(self.settings['verboseLevel'], default_priority)
        balance_text = f'{prefix} BALANCE:'
        balance_xpath = self.selectors['selectors']['balance']

        try:
            element = self.monitor_element(balance_xpath, 20, "get balance")
            if element:
                balance_part = element
                self.logger.info(f"Step {self.step} - {balance_text} {balance_part}", priority)

        except NoSuchElementException:
            self.logger.debug(f"Step {self.step} - Element containing '{prefix} Balance:' was not found.", priority)
        except Exception as e:
            self.logger.warning(f"Step {self.step} - An error occurred: {e}", exc_info=True)

        self.increase_step()

    def get_profit_hour(self, claimed: bool) -> None:
        """
        Get profit per hour.

        Args:
            claimed: True if this is after claiming
        """
        prefix = "After" if claimed else "Before"
        default_priority = 2 if claimed else 3
        priority = max(self.settings['verboseLevel'], default_priority)
        profit_text = f'{prefix} PROFIT/HOUR:'
        profit_xpath = self.selectors['selectors']['storage_profit']

        try:
            element = self.strip_non_numeric(self.monitor_element(profit_xpath, 20, "get profit per hour"))

            if element:
                self.logger.info(f"Step {self.step} - {profit_text} {element}", priority)

        except NoSuchElementException:
            self.logger.debug(f"Step {self.step} - Element containing '{prefix} Profit/Hour:' was not found.", priority)
        except Exception as e:
            self.logger.warning(f"Step {self.step} - An error occurred: {e}", exc_info=True)

        self.increase_step()

    def get_wait_time(self, step_number: str = "108", beforeAfter: str = "pre-claim"):
        """
        Get wait time before next claim.

        Args:
            step_number: Current step number
            beforeAfter: 'pre-claim' or 'post-claim'

        Returns:
            str: Wait time string or "Filled"
        """
        xpath = self.selectors['selectors']['wait_time']
        try:
            wait_time_element = self.monitor_element(xpath, 20, "get the wait time")
            if wait_time_element is not None:
                return wait_time_element
            else:
                self.logger.debug(f"Step {self.step}: Wait time element not found. Clicking the 'Storage' link and retrying...")
                storage_xpath = self.selectors['selectors']['storage_link']
                self.move_and_click(storage_xpath, 30, True, "click the 'storage' link", f"{self.step} recheck", "clickable")
                wait_time_element = self.monitor_element(xpath, 20, "get the wait time after retry")
                if wait_time_element is not None:
                    return wait_time_element
                else:
                    self.logger.debug(f"Step {self.step}: Wait time element still not found after retry.")

        except TimeoutException:
            self.logger.debug(f"Step {self.step}: Timeout occurred while trying to get the wait time.")

        except Exception as e:
            self.logger.debug(f"Step {self.step}: An error occurred: {e}")

        return False


def main() -> None:
    """
    Main entry point for HOT wallet automation.
    """
    claimer = HotClaimer()
    claimer.run()


if __name__ == "__main__":
    main()
