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


class CryptoRankClaimer(Claimer):

    def initialize_settings(self):
        super().initialize_settings()
        self.script = "games/cryptorank.py"
        self.prefix = "CryptoRank:"
        self.url = "https://web.telegram.org/k/#@CryptoRank_app_bot"
        self.pot_full = "Filled"
        self.pot_filling = "to fill"
        self.seed_phrase = None
        self.forceLocalProxy = False
        self.forceRequestUserAgent = False
        self.allow_early_claim = False
        self.start_app_xpath = "//button[.//span[contains(text(),'Start Earning CR Points')]]"

    def __init__(self):
        self.settings_file = "variables.txt"
        self.status_file_path = "status.txt"
        self.wallet_id = ""
        self.daily_reward_text = ""
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

            self.check_opening_screens()

            self.set_cookies()

        except TimeoutException:
            self.output(f"Step {self.step} - Failed to find or switch to the iframe within the timeout period.",1)

        except Exception as e:
            self.output(f"Step {self.step} - An error occurred: {e}",1)

    def check_opening_screens(self):

        # Check for the initial opening scrren
        xpath = "//button[text()='Skip']"
        if self.move_and_click(xpath, 8, True, "initial screen (may not be present)", self.step, "clickable"):
            return True
        else:
            return False

    def full_claim(self):

        self.step = "100"
        self.launch_iframe()
        self.check_opening_screens()

        # Are we farming? if not, start!
        xpath = "//button[text()='Start Farming']"
        self.move_and_click(xpath, 8, True, "initial start farming (may not be present)", self.step, "clickable")

        pre_balance = self.get_balance(False)
        self.increase_step()

        remaining_time = self.get_wait_time()
        if remaining_time:
            matches = re.findall(r'(\d+)([hm])', remaining_time)
            remaining_wait_time = sum(int(value) * (60 if unit == 'h' else 1) for value, unit in matches)
            remaining_wait_time = self.apply_random_offset(remaining_wait_time)
            self.output(f"STATUS: Considering {remaining_time} we'll sleep for {remaining_wait_time}.",2)
            return remaining_wait_time

        self.increase_step()
    
        # We got this far, so let's try to claim!
        xpath = "//button[contains(text(), 'Claim')]"
        success = self.move_and_click(xpath, 20, True, "look for the claim button.", self.step, "visible")
        self.increase_step()

        # And start farming again.
        xpath = "//button[text()='Start Farming']"
        self.move_and_click(xpath, 30, True, "initial start farming (may not be present)", self.step, "clickable")
        self.increase_step()

        # And check the post-claim balance
        post_balance = self.get_balance(True)

        try:
            # Check if pre_balance and post_balance are not None
            if pre_balance is not None and post_balance is not None:
                # Attempt to convert both variables to float
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
        
        # And check for the daily reward.
        self.complete_daily_reward()
       
        # Finally, let's wrap up the time to come back
        if remaining_time:
            matches = re.findall(r'(\d+)([hm])', remaining_time)
            remaining_wait_time = sum(int(value) * (60 if unit == 'h' else 1) for value, unit in matches)
            remaining_wait_time = self.apply_random_offset(remaining_wait_time)
            self.output(f"STATUS: {success_text} {self.daily_reward_text} Let's sleep for {remaining_time}.",2)
            return remaining_wait_time

        return 60
        
    def get_balance(self, claimed=False):
        prefix = "After" if claimed else "Before"
        default_priority = 2 if claimed else 3

        priority = max(self.settings['verboseLevel'], default_priority)

        balance_text = f'{prefix} BALANCE:' if claimed else f'{prefix} BALANCE:'
        balance_xpath = f"//img[contains(@src, 'crystal')]/following-sibling::span[last()]"

        try:
            element = self.monitor_element(balance_xpath, 15, "get balance")
            if element:
                balance_part = element
                self.output(f"Step {self.step} - {balance_text} {balance_part}", priority)
                return balance_part

        except NoSuchElementException:
            self.output(f"Step {self.step} - Element containing '{prefix} Balance:' was not found.", priority)
        except Exception as e:
            self.output(f"Step {self.step} - An error occurred: {str(e)}", priority)

        self.increase_step()

    def get_wait_time(self, step_number="108", beforeAfter="pre-claim", max_attempts=1):
        for attempt in range(1, max_attempts + 1):
            try:
                self.output(f"Step {self.step} - Get the wait time...", 3)
                xpath = "//span[text()='Farming']/following-sibling::div[1]"
                elements = self.monitor_element(xpath, 10, "get claim timer")
                if elements:
                    return elements
                return False
            except Exception as e:
                self.output(f"Step {self.step} - An error occurred on attempt {attempt}: {e}", 3)
                return False

        return False

    def stake_coins(self):
        pass

    def complete_daily_reward(self):
        # Select the Tasks Tab
        xpath = "//a[normalize-space(text())='Tasks']"
        self.move_and_click(xpath, 8, True, "click the 'Tasks' tab", self.step, "clickable")

        # Select the Tasks Tab
        xpath = "//div[span[text()='Daily check']]/following-sibling::div//button[normalize-space(text())='Claim']"
        self.move_and_click(xpath, 8, True, "click the daily reward 'Claim'", self.step, "clickable")
        if self.move_and_click(xpath, 8, True, "confirm the daily reward 'Claim' (hopefully not present)", self.step, "clickable"):
            self.output(f"Step {self.step} - Looks like we successfully claimed the daily reward.", 2)
            self.daily_reward_text = "Claimed the daily reward."
        else:
            self.output(f"Step {self.step} - Looks like the daily reward was already claimed or unsuccessful.", 2)
            self.daily_reward_text = "Daily reward alrady claimed."



def main():
    claimer = CryptoRankClaimer()
    claimer.run()

if __name__ == "__main__":
    main()