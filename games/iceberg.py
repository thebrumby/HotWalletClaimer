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
        self.start_app_xpath = "//span[text()='Play']"
        self.start_app_menu_item = "//a[.//span[contains(@class, 'peer-title') and normalize-space(text())='Iceberg']]"
        self.balance_xpath = f"//p[normalize-space(.)='Your balance']/ancestor::div[2]/p"
        self.time_remaining_xpath = "//p[contains(text(), 'Receive after')]/span"

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

        # Is there an intro screen? if so, clear it!
        xpath = "//button[div[text()='Skip']]"
        self.brute_click(xpath, 20, "pre-start info screen (may not be present)")

        # Are we farming? if not, start!
        xpath = "//button[div[text()='Start farming']]"
        self.brute_click(xpath, 20, "initial start farming (may not be present)")

        pre_balance = self.get_balance(self.balance_xpath, False)
        self.increase_step()

        remaining_time = self.get_wait_time(self.time_remaining_xpath, self.step, "pre-claim")
        if remaining_time:
            self.output(f"STATUS: Claim not yet ready, we'll sleep for {remaining_time} minutes.", 2)
            return min(30,remaining_time)

        self.increase_step()
    
        # We got this far, so let's try to claim!
        xpath = "//button[contains(text(), 'Collect')]"
        success = self.brute_click(xpath, 20, "collect points")
        self.increase_step()

        # And start farming again.
        xpath = "//button[div[text()='Start farming']]"
        self.brute_click(xpath, 20, "post-claim start farming (may not be present)")
        self.increase_step()

        # And check the post-claim balance
        post_balance = self.get_balance(self.balance_xpath, True)

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
        remaining_time = self.get_wait_time(self.time_remaining_xpath, self.step, "post-claim")
        
        # Finally, let's wrap up the time to come back
        if remaining_time:
            self.output(f"STATUS: {success_text}. Let's sleep for {remaining_time} minutes.", 2)
            return remaining_time
        # Finally, if we reached the end with no action, let's come back in an hour
        return 60

def main():
    claimer = IcebergClaimer()
    claimer.run()

if __name__ == "__main__":
    main()
