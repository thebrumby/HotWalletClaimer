import os
import shutil
import sys
import time
import re
import json
import getpass
import random
import subprocess
from PIL import Image
from pyzbar.pyzbar import decode
import qrcode_terminal
import fcntl
from fcntl import flock, LOCK_EX, LOCK_UN, LOCK_NB
from datetime import datetime, timedelta, timezone
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


class SideKickClaimer(Claimer):

    def initialize_settings(self):
        super().initialize_settings()
        self.script = "games/sidefans.py"
        self.prefix = "SideFans:"
        self.url = "https://web.telegram.org/k/#@sidekick_fans_bot"
        self.pot_full = "Filled"
        self.pot_filling = "to fill"
        self.seed_phrase = None
        self.forceLocalProxy = False
        self.forceRequestUserAgent = False
        self.allow_early_claim = True
        self.start_app_xpath = "//div[contains(@class, 'new-message-bot-commands') and div[contains(@class, 'new-message-bot-commands-view') and text()='Play']]"

    def __init__(self):
        self.settings_file = "variables.txt"
        self.status_file_path = "status.txt"
        self.wallet_id = ""
        self.load_settings()
        self.random_offset = random.randint(self.settings['lowestClaimOffset'], self.settings['highestClaimOffset'])
        super().__init__()

    def next_steps(self):
        if self.step:
            pass
        else:
            self.step = "01"

        try:
            self.launch_iframe()
            self.increase_step()

            self.set_cookies()

        except TimeoutException:
            self.output(f"Step {self.step} - Failed to find or switch to the iframe within the timeout period.", 1)

        except Exception as e:
            self.output(f"Step {self.step} - An error occurred: {e}", 1)

    def full_claim(self):
        self.step = "100"

        self.launch_iframe()

        xpath = "//button[contains(text(), 'START')]"
        success = self.move_and_click(xpath, 25, True, "click the 'START' button", self.step, "clickable")
        self.increase_step()

        if success:
            xpath = "//button[contains(text(), 'Awesome!')]"
            next_button = self.move_and_click(xpath, 25, True, "click the 'Awesome!' button", self.step, "clickable")
            self.increase_step()

            xpath = "//button[contains(text(), 'CLAIM')]"
            next_button = self.move_and_click(xpath, 25, True, 'click the "CLAIM" button', self.step, "clickable")
            self.increase_step()

        # Get the original balance before the claim
        original_balance = self.get_balance(False)
        self.increase_step()

        xpath = "//div[normalize-space(text()) = 'Pass']"
        self.move_and_click(xpath, 25, True, "click on the 'Pass' tab", self.step, "visible")
        self.increase_step()

        xpath = "//div[div[text()='Daily check-in']]/following-sibling::div//div[text()='GO']"
        self.move_and_click(xpath, 25, True, "click the 'GO' button on daily checkin task", self.step, "visible")
        self.increase_step()

        xpath = "//button[contains(text(), 'See you tomorrow')]"
        already_claimed = self.move_and_click(xpath, 10, False, "check if already claimed", self.step, "visible")
        if already_claimed:
            self.output("STATUS: The daily reward has already been claimed", 1)
            return self.get_wait_time()
        self.increase_step()

        xpath = "//button[contains(text(), 'Claim')]"
        self.move_and_click(xpath, 25, True, "click the 'Claim' button", self.step, "clickable")
        self.increase_step()

        self.quit_driver()
        self.launch_iframe()

        # Get the new balance after claiming
        new_balance = self.get_balance(True)
        self.increase_step()

        balance_diff = None  # Default in case balance difference can't be determined
        if new_balance:
            try:
                # Calculate the balance difference
                balance_diff = float(new_balance) - float(original_balance)
                if balance_diff > 0:
                    self.output(f"STATUS: Making a claim increased the balance by {balance_diff}", 1)
                    return self.get_wait_time()
            except Exception as e:
                self.output(f"Step {self.step} - Error calculating balance difference: {e}", 2)
        self.output(f"STATUS: Unable to confirm balance increased after claim, let's double check in 2 hours.", 1)
        return 120

    def get_balance(self, claimed=False):
        prefix = "After" if claimed else "Before"
        priority = 2  # Always set to 2

        balance_text = f"{prefix} BALANCE:"
        balance_xpath = "//div[text()='DIAMONDS']/preceding-sibling::span"

        attempts = 0
        max_attempts = 3

        while attempts < max_attempts:
            try:
                # Monitor element with the new XPath
                element = self.monitor_element(balance_xpath, 10, "get balance")
                if element:
                    balance_value = self.strip_html_and_non_numeric(element)

                    try:
                        # Convert to float directly as it's just a number
                        balance_value = float(balance_value)
                        self.output(f"Step {self.step} - {balance_text} {balance_value}", priority)

                        # Check if the balance is 0, if so, retry up to max_attempts
                        if balance_value == 0.0:
                            attempts += 1
                            self.output(f"Step {self.step} - Balance is 0.0, retrying {attempts}/{max_attempts}", priority)
                            continue  # Retry if balance is 0.0
                        return balance_value
                    except ValueError:
                        self.output(f"Step {self.step} - Could not convert balance '{balance_value}' to a number.", priority)
                        return None
                else:
                    self.output(f"Step {self.step} - Balance element not found.", priority)
                    return None
            except Exception as e:
                self.output(f"Step {self.step} - An error occurred: {e}", priority)
                return None

        # If balance was 0.0 after all attempts
        self.output(f"Step {self.step} - Balance remained 0.0 after {max_attempts} attempts.", priority)
        return 0.0

    def get_wait_time(self, step_number="108", beforeAfter="pre-claim", max_attempts=1):
        current_time_utc = datetime.now(timezone.utc)

        # Calculate the start and end times for the next day (08:00 to 16:00)
        next_day_8am = (current_time_utc + timedelta(days=1)).replace(hour=8, minute=0, second=0, microsecond=0)
        next_day_4pm = (current_time_utc + timedelta(days=1)).replace(hour=16, minute=0, second=0, microsecond=0)

        # Get the total minutes between 08:00 and 16:00
        minutes_range = int((next_day_4pm - next_day_8am).total_seconds() / 60)

        # Pick a random number of minutes within this range
        random_minutes = random.randint(0, minutes_range)

        # Calculate the random time between 08:00 and 16:00
        random_time = next_day_8am + timedelta(minutes=random_minutes)

        # Calculate the number of minutes from the current time to the random time
        time_to_random_time = int((random_time - current_time_utc).total_seconds() / 60)

        return time_to_random_time


def main():
    claimer = SideKickClaimer()
    claimer.run()


if __name__ == "__main__":
    main()