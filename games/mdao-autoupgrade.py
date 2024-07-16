
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

class MDAOAUClaimer(Claimer):

    def __init__(self):

        self.settings_file = "variables.txt"
        self.status_file_path = "status.txt"
        self.load_settings()
        self.random_offset = random.randint(min(self.settings['lowestClaimOffset'], 0), min(self.settings['highestClaimOffset'], 0))
        self.script = "games/mdao-autoupgrade.py"
        self.prefix = "MDAO-Auto:"
        self.url = "https://web.telegram.org/k/#@Mdaowalletbot"
        self.pot_full = "Filled"
        self.pot_filling = "to fill"
        self.seed_phrase = None
        self.forceLocalProxy = False
        self.forceRequestUserAgent = False

        super().__init__()

        self.start_app_xpath = "//span[contains(text(), 'Play&Earn')]"

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

        def return_minutes(wait_time_text):
            if wait_time_text != "Filled":
                matches = re.findall(r'(\d+)([hm])', wait_time_text)
                remaining_wait_time = (sum(int(value) * (60 if unit == 'h' else 1) for value, unit in matches)) + self.random_offset
                return remaining_wait_time
            return 120

        self.step = "100"

        self.launch_iframe()

        self.get_balance(False)

        remaining_wait_time = return_minutes(self.get_wait_time(self.step, "pre-claim"))
        self.increase_step()

        if remaining_wait_time < 5 or self.settings["forceClaim"]:
            self.settings['forceClaim'] = True
            self.output(f"Step {self.step} - the remaining time to claim is less than the random offset, so applying: settings['forceClaim'] = True", 3)
        else:
            self.output(f"STATUS: Wait time is {remaining_wait_time} minutes and off-set of {self.random_offset}.", 1)
            return remaining_wait_time + self.random_offset
        # Try to claim
        xpath = "//div[text()='CLAIM']"
        self.move_and_click(xpath, 30, True, "Click the claim button", self.step, "clickable")
        # Get the balance afterwards
        available_balance = self.get_balance(True)
        # Get remaining wait time for after the upgrade.
        remaining_wait_time = return_minutes(self.get_wait_time(self.step, "post-claim"))
        self.increase_step()
        # Let's see if we can upgrade?
        try:
            available_balance = float(available_balance) if available_balance else 0
            xpath = "//div[text()='Workbench']"
            self.move_and_click(xpath, 30, True, "look for cost upgrade tab", self.step, "clickable")
            xpath = "//div[contains(text(), 'to reach next level')]"
            self.move_and_click(xpath, 30, False, "look upgrade cost in ZP", self.step, "visible")
            upgrade_cost = self.strip_html_and_non_numeric(self.monitor_element(xpath))
            upgrade_cost = float(upgrade_cost.replace(',', '').strip()) if upgrade_cost else 0
            self.output(f"Step {self.step} - the upgrade cost is {upgrade_cost}.",3)
            shortfall = available_balance - upgrade_cost
            if not shortfall:
                xpath = "//div[contains(text(), 'LVL UP')]"
                self.move_and_click(xpath, 30, True, "look for cost upgrade tab", self.step, "clickable")
                self.output(f"STATUS: We have spent {upgrade_cost} ZP to upgrade the mining speed.",1)
            else:
                self.output(f"Step {self.step} - there is a shortfall of {shortfall} ZP to upgrade the mining speed.",2)

        except (ValueError, AttributeError, TypeError) as e:
            self.output(f"Step {self.step} - Unable to correctly calculate the upgrade cost.", 2)

        self.random_offset = random.randint(min(self.settings['lowestClaimOffset'], 0), min(self.settings['highestClaimOffset'], 0))
        self.output(f"STATUS: Wait time is {remaining_wait_time} minutes and off-set of {self.random_offset}.", 1)
        return remaining_wait_time + self.random_offset

    def get_balance(self, claimed=False):
        prefix = "After" if claimed else "Before"
        default_priority = 2 if claimed else 3

        priority = max(self.settings['verboseLevel'], default_priority)

        balance_text = f'{prefix} ZP BALANCE:' if claimed else f'{prefix} BALANCE:'
        balance_xpath = f"//div[@data-tooltip-id='balance']/div[1]"
        balance_part = None

        try:
            self.move_and_click(balance_xpath, 30, False, "look for ZP balance", self.step, "visible")
            balance_part = self.strip_html(self.monitor_element(balance_xpath))
            self.output(f"Step {self.step} - {balance_text} {balance_part}", priority)
        except NoSuchElementException:
            self.output(f"Step {self.step} - Element containing '{prefix} Balance:' was not found.", priority)
        except Exception as e:
            self.output(f"Step {self.step} - An error occurred: {str(e)}", priority)

        self.increase_step()
        return balance_part  # Added return statement to ensure balance_part is returned

    def get_wait_time(self, step_number="108", beforeAfter="pre-claim", max_attempts=1):
        for attempt in range(1, max_attempts + 1):
            try:
                self.output(f"Step {self.step} - check if the timer is elapsing...", 3)
                xpath = "//div[contains(text(), 'until claim')]"
                pot_full_value = self.strip_html(self.monitor_element(xpath, 15))
                return pot_full_value
            except Exception as e:
                self.output(f"Step {self.step} - An error occurred on attempt {attempt}: {e}", 3)
                return "Unknown"
        return "Unknown"

def main():
    claimer = MDAOAUClaimer()
    claimer.run()

if __name__ == "__main__":
    main()