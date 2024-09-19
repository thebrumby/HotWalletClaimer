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

import requests
import urllib.request
from claimer import Claimer

class SpellClaimer(Claimer):

    def initialize_settings(self):
        super().initialize_settings()
        self.script = "games/spell.py"
        self.prefix = "Spell:"
        self.url = "https://web.telegram.org/k/#@spell_wallet_bot"
        self.pot_full = "Filled"
        self.pot_filling = "to fill"
        self.seed_phrase = None
        self.forceLocalProxy = False
        self.forceRequestUserAgent = False
        self.allow_early_claim = False
        self.start_app_xpath = "//div[@class='reply-markup-row']//span[contains(text(),'Open Spell')]"

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
            
            # Get balance
            self.get_balance(False)

            # Final Housekeeping
            self.set_cookies()

        except TimeoutException:
            self.output(f"Step {self.step} - Failed to find or switch to the iframe within the timeout period.", 1)

        except Exception as e:
            self.output(f"Step {self.step} - An error occurred: {e}", 1)

    def full_claim(self):
        # Initialize status_text
        status_text = ""

        # Launch iframe
        self.step = "100"
        self.launch_iframe()

        # Capture the balance before the claim
        before_balance = self.get_balance(False)

        # Brute force the claim to collect all '%' and then spin the wheel:
        xpath = "//div[contains(text(), '%')]"
        if self.brute_click(xpath, 12, "click the 'Claim' button"):
            self.output(f"Step {self.step} - Claim was available and clicked.", 3)
            self.increase_step()
            
            # Spin the wheel
            xpath = "//p[contains(., 'Spin the Wheel')]"
            self.move_and_click(xpath, 10, True, "spin the wheel", self.step, "clickable")
            self.increase_step()
            
            xpath = "//*[contains(text(), 'GOT IT')]"
            self.move_and_click(xpath, 10, True, "check for 'Got it' message (may not be present)", self.step, "clickable")
            self.increase_step()

            # Capture the balance after the claim
            after_balance = self.get_balance(True)

            # Calculate balance difference
            try:
                if before_balance is not None and after_balance is not None:
                    bal_diff = after_balance - before_balance
                    status_text += f"Claim submitted - balance increase {bal_diff} "
            except Exception as e:
                self.output(f"Step {self.step} - An error occurred while calculating balance difference: {e}", 1)
        else:
            self.output(f"Step {self.step} - Claim button not present.", 3)

        # Get the wait timer if present
        remaining_wait_time = self.get_wait_time(self.step, "post-claim")
            
        # Do the Daily Puzzle from GitHub
        if self.daily_reward():
            status_text += "Daily Puzzle submitted"

        if not remaining_wait_time:
            self.output(f"STATUS: The wait timer is still showing: Filled.", 1)
            self.output(f"Step {self.step} - This means either the claim failed, or there is lag in the game.", 1)
            self.output(f"Step {self.step} - We'll check back in 1 hour to see if the claim processed and if not try again.", 2)
            return 60

        remaining_time = self.apply_random_offset(remaining_wait_time)
        
        # Output final status
        self.output(f"STATUS: {status_text}", 3)

        self.output(f"STATUS: Original wait time {remaining_wait_time} minutes, we'll sleep for {remaining_time} minutes after random offset.", 1)
        return max(remaining_time,60)

    def daily_reward(self):
        # Switch to the Quests tab and check if Puzzle already solved
        xpath = "//p[contains(., 'Quests')]"
        success = self.move_and_click(xpath, 10, True, "click on 'Quests' tab", self.step, "clickable")
        self.increase_step()
        
        if not success:
            self.quit_driver()
            self.launch_iframe()
            self.move_and_click(xpath, 10, True, "click on 'Quests' tab", self.step, "clickable")
            self.increase_step()

        xpath = "//div[contains(@class, 'css-ehjmbb')]//p[contains(text(), 'Done')]"
        success = self.move_and_click(xpath, 10, True, "click on 'Daily Puzzle' link", self.step, "clickable")
        self.increase_step()
        if success:
            return False

        xpath = "//p[contains(., 'Daily Puzzle')]"
        self.move_and_click(xpath, 10, True, "click on 'Daily Puzzle' link", self.step, "clickable")
        self.increase_step()

        # Fetch the 4-digit code from the GitHub file using urllib
        url = "https://raw.githubusercontent.com/thebrumby/HotWalletClaimer/main/extras/rewardtest"
        try:
            with urllib.request.urlopen(url) as response:
                content = response.read().decode('utf-8').strip()
            self.output(f"Step {self.step} - Fetched code from GitHub: {content}", 3)
        except Exception as e:
            # Handle failure to fetch code
            self.output(f"Step {self.step} - Failed to fetch code from GitHub: {str(e)}", 2)
            return False

        self.increase_step()

        # Translate the numbers from GitHub to the symbols in the game
        for index, digit in enumerate(content):
            xpath = f"//div[@class='css-k0i5go'][{digit}]"
            
            if self.move_and_click(xpath, 30, True, f"click on the path corresponding to digit {digit}", self.step, "clickable"):
                self.output(f"Step {self.step} - Clicked on element corresponding to digit {digit}.", 2)
            else:
                # Handle failure to click on an element
                self.output(f"Step {self.step} - Element corresponding to digit {digit} not found or not clickable.", 1)

        self.increase_step()

        # Finish with some error checking
        invalid_puzzle_xpath = "//div[contains(text(), 'Invalid puzzle code')]/ancestor::div[contains(@class, 'chakra-alert')]"
        if self.move_and_click(invalid_puzzle_xpath, 30, True, "check if alert is present", self.step, "visible"):
            # Alert for invalid puzzle code is present
            self.output(f"Step {self.step} - Alert for invalid puzzle code is present.", 2)
        else:
            # Alert for invalid puzzle code is not present
            self.output(f"Step {self.step} - Alert for invalid puzzle code is not present.", 1)

        self.output(f"Step {self.step} - Completed daily reward sequence successfully.", 2)
        return True

    def get_balance(self, claimed=False):
        prefix = "After" if claimed else "Before"
        default_priority = 2 if claimed else 3

        # Dynamically adjust the log priority
        priority = max(self.settings['verboseLevel'], default_priority)

        # Construct text based on before/after
        balance_text = f'{prefix} BALANCE:' if claimed else f'{prefix} BALANCE:'
        balance_xpath = "//div[@class='css-fm4un4']"

        try:
            element = self.strip_html_and_non_numeric(self.monitor_element(balance_xpath, 15, "get balance"))

            # Check if element is not None and process the balance
            if element:
                balance_float = float(element)
                self.output(f"Step {self.step} - {balance_text} {balance_float}", priority)
                return balance_float
            else:
                self.output(f"Step {self.step} - {balance_text} not found or not numeric.", priority)
                return None

        except NoSuchElementException:
            self.output(f"Step {self.step} - Element containing '{prefix} Balance:' was not found.", priority)
            return None
        except Exception as e:
            self.output(f"Step {self.step} - An error occurred: {str(e)}", priority)  # Provide error as string for logging
            return None

        # Increment step function, assumed to handle next step logic
        self.increase_step()

    def get_wait_time(self, step_number="108", beforeAfter="pre-claim"):
        try:
            self.output(f"Step {self.step} - Get the wait time...", 3)
    
            # XPath to find the div element with the specific class
            xpath = "//div[@class='css-1dgzots']"
            wait_time_text = self.monitor_element(xpath, 10, "claim timer")
    
            # Check if wait_time_text is not empty
            if wait_time_text:
                wait_time_text = wait_time_text.strip()
                self.output(f"Step {self.step} - Extracted wait time text: '{wait_time_text}'", 3)
    
                # Remove any spaces to standardize the format
                wait_time_text_clean = wait_time_text.replace(" ", "")
    
                # Regular expression to match patterns like '5h30m', '5h', '30m'
                pattern = r'(?:(\d+)h)?(?:(\d+)m)?'
                match = re.match(pattern, wait_time_text_clean)
    
                if match:
                    hours = match.group(1)
                    minutes = match.group(2)
                    total_minutes = 0
    
                    if hours:
                        total_minutes += int(hours) * 60
                    if minutes:
                        total_minutes += int(minutes)
    
                    self.output(f"Step {self.step} - Total wait time in minutes: {total_minutes}", 3)
                    return total_minutes if total_minutes > 0 else False
                else:
                    # If the pattern doesn't match, return False
                    self.output(f"Step {self.step} - Wait time pattern not matched in text: '{wait_time_text}'", 3)
                    return False
            else:
                # No text found in the element
                self.output(f"Step {self.step} - No wait time text found.", 3)
                return False
        except Exception as e:
            self.output(f"Step {self.step} - An error occurred: {e}", 3)
            return False

def main():
    claimer = SpellClaimer()
    claimer.run()

if __name__ == "__main__":
    main()
