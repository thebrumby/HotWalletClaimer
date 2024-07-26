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

from mdao import MDAOClaimer

class MDAOAUClaimer(MDAOClaimer):

    def initialize_settings(self):
        super().initialize_settings()
        self.script = "games/mdao-autoupgrade.py"
        self.prefix = "MDAO-Auto:"

    def __init__(self):
        super().__init__()
        self.start_app_xpath = "//span[contains(text(), 'Play&Earn')]"

    def full_claim(self):

        def return_minutes(wait_time_text, random_offset=0):
            matches = re.findall(r'(\d+)([hms])', wait_time_text)
            total_minutes = 0
            for value, unit in matches:
                if unit == 'h':
                    total_minutes += int(value) * 60
                elif unit == 'm':
                    total_minutes += int(value)
                elif unit == 's':
                    total_minutes += int(value) / 60  # Convert seconds to minutes
            remaining_wait_time = total_minutes
            return int(remaining_wait_time)

        self.step = "100"

        self.launch_iframe()

        self.get_balance(False)

        remaining_wait_time = self.get_wait_time(self.step, "pre-claim")

        if remaining_wait_time == "Filled":
            self.settings['forceClaim'] = True
            remaining_wait_time = 0
        elif remaining_wait_time == "Unknown":
            return 30
        else:
            remaining_wait_time = return_minutes(remaining_wait_time)
            self.output(f"STATUS: Pot not yet full, let's sleep for {remaining_wait_time} minutes.", 1)
            return remaining_wait_time

        self.increase_step()

        if int(remaining_wait_time) < 5 or self.settings["forceClaim"]:
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

        # Check the mining speed:
        self.get_profit_hour(True)

        # Let's see if we can upgrade?
        try:
            available_balance = float(available_balance) if available_balance else 0
            xpath = "//div[text()='Workbench']"
            self.move_and_click(xpath, 30, True, "look for cost upgrade tab", self.step, "clickable")
            xpath = "//div[contains(text(), 'to reach next level')]"
            self.move_and_click(xpath, 30, False, "look upgrade cost in ZP", self.step, "visible")
            upgrade_cost = self.strip_html_and_non_numeric(self.monitor_element(xpath))
            upgrade_cost = float(upgrade_cost.replace(',', '').strip()) if upgrade_cost else 0
            self.output(f"Step {self.step} - the upgrade cost is {upgrade_cost}.", 3)
            shortfall = available_balance - upgrade_cost
            if shortfall > 0:
                xpath = "//div[contains(text(), 'LVL UP')]"
                self.move_and_click(xpath, 30, True, "click the LVL UP button", self.step, "clickable")
                xpath = "//div[contains(text(), 'CONFIRM')]"
                button = self.move_and_click(xpath, 30, False, "click the Confirm button", self.step, "clickable")
                if button:
                    success = self.driver.execute_script("arguments[0].click();", button)
                    if success:
                        self.output(f"STATUS: We have spent {upgrade_cost} ZP to upgrade the mining speed.", 1)
            else:
                self.output(f"Step {self.step} - there is a shortfall of {shortfall} ZP to upgrade the mining speed.", 2)

        except (ValueError, AttributeError, TypeError) as e:
            self.output(f"Step {self.step} - Unable to correctly calculate the upgrade cost.", 2)

        self.random_offset = random.randint(max(self.settings['lowestClaimOffset'], 0), max(self.settings['highestClaimOffset'], 0))
        self.output(f"STATUS: Wait time is {remaining_wait_time} minutes and off-set of {self.random_offset}.", 1)
        return remaining_wait_time + self.random_offset

def main():
    claimer = MDAOAUClaimer()
    claimer.run()

if __name__ == "__main__":
    main()