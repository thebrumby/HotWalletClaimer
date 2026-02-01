"""
Blum Claimer - Improved Version
Type hints, error handling, and security improvements.
"""

import os
import sys
import time
import re
from typing import Optional, Tuple, List
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException

from claimer_improved import Claimer, DEFAULT_TIMEOUT, ELEMENT_CLICK_TIMEOUT, PAGE_LOAD_TIMEOUT


class BlumClaimer(Claimer):
    """
    Automate Blum Telegram game claiming and farming.
    """

    def initialize_settings(self) -> None:
        """Initialize game-specific settings."""
        super().initialize_settings()
        self.script = "games/blum.py"
        self.prefix = "Blum:"
        self.url = "https://web.telegram.org/k/#@BlumCryptoBot"
        self.pot_full = "Filled"
        self.pot_filling = "to fill"
        self.seed_phrase = None
        self.forceLocalProxy = True
        self.forceRequestUserAgent = False
        self.allow_early_claim = False
        self.start_app_xpath = "//button[span[contains(text(), 'Launch Blum')]]"
        self.start_app_menu_item = "//div[contains(@class, 'dialog-title')]//span[contains(text(), 'Blum')]"

    def __init__(self) -> None:
        """Initialize the claimer."""
        self.settings_file = "variables.txt"
        self.status_file_path = "status.txt"
        self.wallet_id = ""
        self.load_settings()
        self.random_offset = random.randint(self.settings['lowestClaimOffset'], self.settings['highestClaimOffset'])
        super().__init__()

    def next_steps(self) -> None:
        """Execute next steps to launch the game."""
        if self.step:
            pass
        else:
            self.step = "01"

        try:
            self.launch_iframe()
            self.increase_step()
            self.set_cookies()
        except TimeoutException:
            self.output(f"Step {self.step} - Failed to find or switch to iframe within timeout period.", 1)
        except Exception as e:
            self.output(f"Step {self.step} - An error occurred: {e}", 1)

    def full_claim(self) -> float:
        """
        Execute the full claim process and return wait time.

        Returns:
            Wait time in minutes until next claim
        """
        self.step = "100"
        self.launch_iframe()

        # Handle daily rewards
        xpath = "//span[contains(text(), 'Your daily rewards')]"
        present = self.move_and_click(xpath, 20, False, "check for daily reward", self.step, "visible")
        self.increase_step()
        reward_text = None

        if present:
            xpath = "(//div[@class='count'])[1]"
            points = self.move_and_click(xpath, ELEMENT_CLICK_TIMEOUT, False, "get daily points", self.step, "visible")
            xpath = "(//div[@class='count'])[2]"
            days = self.move_and_click(xpath, ELEMENT_CLICK_TIMEOUT, False, "get consecutive days", self.step, "visible")
            reward_text = f"Daily rewards: {points.text} points & {days.text} days."
            xpath = "//button[.//span[text()='Continue']]"
            self.move_and_click(xpath, ELEMENT_CLICK_TIMEOUT, True, "click continue", self.step, "clickable")
            self.increase_step()

        xpath = "//button[.//div[text()='Continue']]"
        self.move_and_click(xpath, ELEMENT_CLICK_TIMEOUT, True, "click continue", self.step, "clickable")
        self.increase_step()

        xpath = "//button[.//span[contains(text(), 'Start farming')]][1]"
        self.move_and_click(xpath, ELEMENT_CLICK_TIMEOUT, True, "start farming", self.step, "clickable")
        self.increase_step()

        self.get_balance(claimed=False)
        wait_time_text = self.get_wait_time(self.step, "pre-claim")

        if not wait_time_text:
            return 60

        if wait_time_text != self.pot_full:
            matches = re.findall(r'(\d+)([hm])', wait_time_text)
            remaining_wait_time = (
                sum(int(value) * (60 if unit == 'h' else 1) for value, unit in matches)
                + self.random_offset
            )

            if remaining_wait_time < 5 or self.settings["forceClaim"]:
                self.settings['forceClaim'] = True
                self.output(
                    f"Step {self.step} - Remaining time < offset, force claiming enabled.",
                    3
                )
            else:
                self.output(f"STATUS: Still {wait_time_text}, offset {self.random_offset} min. Waiting.", 1)
                return remaining_wait_time

        try:
            self.output(f"Step {self.step} - Pre-claim wait: {wait_time_text}, offset: {self.random_offset} min.", 1)
            self.increase_step()

            if wait_time_text == self.pot_full or self.settings['forceClaim']:
                try:
                    xpath = "//button[.//div[contains(text(), 'Claim')]]"
                    self.move_and_click(xpath, ELEMENT_CLICK_TIMEOUT, True, "click claim", self.step, "clickable")
                    self.increase_step()

                    time.sleep(5)

                    xpath = "//button[.//span[contains(text(), 'Start farming')]][1]"
                    self.move_and_click(xpath, ELEMENT_CLICK_TIMEOUT, True, "start farming", self.step, "clickable")
                    self.increase_step()

                    self.output(f"Step {self.step} - Waiting 10 seconds for totals to update...", 3)
                    time.sleep(10)

                    wait_time_text = self.get_wait_time(self.step, "post-claim")
                    matches = re.findall(r'(\d+)([hm])', wait_time_text)
                    total_wait_time = self.apply_random_offset(
                        sum(int(value) * (60 if unit == 'h' else 1) for value, unit in matches)
                    )
                    self.increase_step()

                    self.get_balance(claimed=True)

                    if wait_time_text == self.pot_full:
                        self.output(
                            f"Step {self.step} - Timer still showing 'Filled'. "
                            f"Claim may have failed or is delayed >4 minutes.",
                            1
                        )
                        self.output(
                            f"Step {self.step} - Will retry in 1 hour.",
                            2
                        )
                    else:
                        self.output(
                            f"STATUS: Post-claim wait: {wait_time_text}, new timer: {total_wait_time} min. {reward_text}",
                            1
                        )
                    return max(60, total_wait_time)

                except TimeoutException:
                    self.output("STATUS: Claim process timed out. Retrying in 1 hour.", 1)
                    return 60
                except Exception as e:
                    self.output(f"STATUS: Error during claim: {e}. Retrying in 1 hour.", 1)
                    return 60
            else:
                matches = re.findall(r'(\d+)([hm])', wait_time_text)
                if matches:
                    total_time = sum(int(value) * (60 if unit == 'h' else 1) for value, unit in matches) + 1
                    total_time = max(5, total_time)
                    self.output(
                        f"Step {self.step} - Not time to claim yet. Waiting {total_time} minutes.",
                        2
                    )
                    return total_time
                else:
                    self.output(f"Step {self.step} - No wait time data. Checking again in 1 hour.", 2)
                    return 60
        except Exception as e:
            self.output(f"Step {self.step} - Unexpected error: {e}", 1)
            return 60

    def get_balance(self, claimed: bool = False) -> Optional[float]:
        """
        Get current balance.

        Args:
            claimed: Whether balance is after claim

        Returns:
            Balance value or None if not found
        """
        prefix = "After" if claimed else "Before"
        default_priority = 2 if claimed else 3
        priority = max(self.settings['verboseLevel'], default_priority)

        balance_xpath = f"//div[@class='balance']//div[@class='kit-counter-animation value']"

        try:
            element = WebDriverWait(self.driver, 10).until(
                EC.visibility_of_element_located((By.XPATH, balance_xpath))
            )

            if element:
                char_elements = element.find_elements(By.XPATH, ".//div[@class='el-char']")
                balance_part = ''.join([char.text for char in char_elements]).strip()
                self.output(f"Step {self.step} - {prefix} BALANCE: {balance_part}", priority)
                return float(balance_part)
        except NoSuchElementException:
            self.output(f"Step {self.step} - Element containing '{prefix} Balance:' was not found.", priority)
        except Exception as e:
            self.output(f"Step {self.step} - An error occurred: {str(e)}", priority)

        self.increase_step()
        return None

    def get_wait_time(
        self,
        step_number: str = "108",
        before_after: str = "pre-claim",
        max_attempts: int = 1
    ) -> Optional[str]:
        """
        Get the current wait time status.

        Args:
            step_number: Current step number
            before_after: Whether checking before or after claim
            max_attempts: Maximum number of retry attempts

        Returns:
            Wait time string or None
        """
        for attempt in range(1, max_attempts + 1):
            try:
                self.output(f"Step {self.step} - Checking wait time status...", 3)

                # Check if timer is still running
                xpath = "//div[@class='time-left']"
                wait_time_value = self.monitor_element(xpath, ELEMENT_CLICK_TIMEOUT, "check timer")

                if wait_time_value:
                    return wait_time_value

                # Check if pot is full
                xpath = "//button[.//div[contains(text(), 'Claim')]]"
                pot_full_value = self.monitor_element(xpath, ELEMENT_CLICK_TIMEOUT, "check claim button")
                if pot_full_value:
                    return self.pot_full

                return None
            except Exception as e:
                self.output(f"Step {self.step} - Error on attempt {attempt}: {e}", 3)
                return None

        return None

    def apply_random_offset(self, minutes: int) -> int:
        """
        Apply random offset to wait time.

        Args:
            minutes: Base wait time in minutes

        Returns:
            Wait time with random offset applied
        """
        return minutes + self.random_offset


def main() -> None:
    """Main entry point."""
    claimer = BlumClaimer()
    claimer.run()


if __name__ == "__main__":
    main()
