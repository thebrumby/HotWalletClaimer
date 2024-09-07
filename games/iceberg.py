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
from selenium.common.exceptions import NoSuchElementException, TimeoutException, StaleElementReferenceException, ElementClickInterceptedException, UnexpectedAlertPresentException
from datetime import datetime, timedelta
from selenium.webdriver.chrome.service import Service as ChromeService
import requests

from claimer import Claimer

class IcebergClaimer(Claimer):

    def initialize_settings(self):
        super().initialize_settings()
        self.script = "games/iceberg.py"
        self.prefix = "Iceberg:"
        self.url = "https://web.telegram.org/k/#@IcebergAppBot"
        self.forceLocalProxy = False
        self.forceRequestUserAgent = False
        self.allow_early_claim = False
        self.start_app_xpath = "//div[text()='Play']"

    def __init__(self):
        self.settings_file = "variables.txt"
        self.status_file_path = "status.txt"
        self.wallet_id = ""
        self.load_settings()
        self.random_offset = random.randint(max(self.settings['lowestClaimOffset'], 0), max(self.settings['highestClaimOffset'], 0))
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

        # Are we farming? if not, start!
        xpath = "//button[div[text()='Start farming']]"
        self.move_and_click(xpath, 8, True, "initial start farming (may not be present)", self.step, "clickable")

        pre_balance = self.get_balance(False)
        self.increase_step()

        remaining_time = self.get_wait_time()
        if remaining_time:
            try:
                # Attempt to convert the remaining time to minutes
                remaining_wait_time = self.convert_to_minutes(remaining_time)
                remaining_wait_time = round(self.convert_to_minutes(remaining_time), 1)
                remaining_wait_time = self.apply_random_offset(remaining_wait_time)
                self.output(f"STATUS: Considering {remaining_time}, we'll sleep for {remaining_wait_time} minutes.", 2)
                return remaining_wait_time
            except Exception as e:
                # Handle unexpected errors during time calculation
                self.output(f"Step {self.step} - Error during time calculation: {str(e)}", 2)

        self.increase_step()
    
        # We got this far, so let's try to claim!
        xpath = "//button[contains(text(), 'Collect')]"
        success = self.move_and_click(xpath, 20, True, "look for the claim button.", self.step, "visible")
        self.increase_step()

        # And start farming again.
        xpath = "//button[div[text()='Start farming']]"
        self.move_and_click(xpath, 30, True, "start farming after claim (may not be present)", self.step, "clickable")
        self.increase_step()

        # And check the post-claim balance
        post_balance = self.get_balance(True)

        try:
            if pre_balance is not None and post_balance is not None:
                pre_balance_float = float(pre_balance)
                post_balance_float = float(post_balance)
                if post_balance_float > pre_balance_float:
                    success_text = "Claim successful."
                else:
                    success_text = "Claim may have failed."
            else:
                success_text = "Claim validation failed due to missing balance information."
        except ValueError:
            success_text = "Claim validation failed due to invalid balance format."

        self.increase_step()

        # Store the wait time for later
        remaining_time = self.get_wait_time()
        
        # Finally, let's wrap up the time to come back
        if remaining_time:
            try:
                # Handle time calculations safely within try block
                remaining_wait_time = self.convert_to_minutes(remaining_time)
                remaining_wait_time = round(self.convert_to_minutes(remaining_time), 1)
                remaining_wait_time = self.apply_random_offset(remaining_wait_time)
                self.output(f"STATUS: {success_text} {self.daily_reward_text}. Let's sleep for {remaining_wait_time} minutes.", 2)
                return remaining_wait_time
            except Exception as e:
                self.output(f"Step {self.step} - Error during time calculation: {str(e)}", 2)

        return 60
        
    def get_balance(self, claimed=False):
        balance_xpath = "//p[text()='Your balance']/following-sibling::p"

        try:
            element = self.monitor_element(balance_xpath, 15, "get balance")
            if element:
                balance_part = element
                self.output(f"Step {self.step} - {'After' if claimed else 'Before'} BALANCE: {balance_part}", 2 if claimed else 3)
                return balance_part

        except NoSuchElementException:
            self.output(f"Step {self.step} - Element containing balance was not found.", 2 if claimed else 3)
        except Exception as e:
            self.output(f"Step {self.step} - An error occurred: {str(e)}", 2 if claimed else 3)

        self.increase_step()

    def get_wait_time(self, step_number="108", beforeAfter="pre-claim", max_attempts=1):
        wait_time_xpath = "//p[contains(text(), 'Receive after')]/span"
        for attempt in range(1, max_attempts + 1):
            try:
                self.output(f"Step {self.step} - Get the wait time...", 3)
                element = self.monitor_element(wait_time_xpath, 10, "get claim timer")
                if element:
                    return element
                return False
            except Exception as e:
                self.output(f"Step {self.step} - An error occurred on attempt {attempt}: {e}", 3)
                return False

        return False

    def convert_to_minutes(self, time_string):
        try:
            h, m, s = map(int, time_string.split(':'))
            return h * 60 + m + s / 60
        except ValueError:
            self.output(f"Step {self.step} - Failed to parse time string {time_string}", 2)
            return 0

def main():
    claimer = IcebergClaimer()
    claimer.run()

if __name__ == "__main__":
    main()