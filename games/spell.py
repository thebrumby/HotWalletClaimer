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
import requests
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

            # Attempt to interact with elements within the iframe.
            xpath = "//*[contains(text(), 'Roadmap')]"
            self.target_element = self.move_and_click(xpath, 30, False, "wait until 'Roadmap' disappears (may not be present)", self.step, "invisible")
            self.increase_step()

            # Then look for the seed phase textarea:
            xpath = "//textarea[@placeholder='Seed Phrase']"
            input_field = self.move_and_click(xpath, 30, True, "locate seedphrase textbox", self.step, "clickable")
            if not self.imported_seedphrase:
                self.imported_seedphrase = self.validate_seed_phrase()
            input_field.send_keys(self.imported_seedphrase) 
            self.output(f"Step {self.step} - Was successfully able to enter the seed phrase...",3)
            self.increase_step()

            # Click the continue button after seed phrase entry:
            recover_wallet_xpath = "//button[contains(text(), 'Recover Wallet')]"
            wallet_check_xpath = "//p[contains(text(), 'Wallet')]"
            start_time = time.time()
            timeout = 60  # seconds

            while time.time() - start_time < timeout:
                if self.move_and_click(recover_wallet_xpath, 10, False, "check for success", self.step, "visible"):
                    self.increase_step()
                    self.click_element(recover_wallet_xpath, 30, "Click 'Recover Wallet'")
                    self.increase_step()
                    if self.move_and_click(wallet_check_xpath, 10, False, "check if wallet tab visible (may not be present)", "08", "visible"):
                        self.increase_step()
                        self.output(f"Step {self.step} - The wallet tab is now visible...",3)
                        break  # Exit loop if the Wallet check element is found

            self.increase_step()

            # Final Housekeeping
            self.set_cookies()

        except TimeoutException:
            self.output(f"Step {self.step} - Failed to find or switch to the iframe within the timeout period.",1)

        except Exception as e:
            self.output(f"Step {self.step} - An error occurred: {e}",1)

    def full_claim(self):
        # Launch iframe
        self.step = "100"
        self.launch_iframe()

        # Wait for 'Roadmap' to disappear
        xpath = "//*[contains(text(), 'Roadmap')]"
        self.target_element = self.move_and_click(xpath, 30, False, "wait until 'Roadmap' disappears (may not be present)", self.step, "invisible")
        self.increase_step()

        # Get balance
        self.get_balance(False)

        # Click on the Storage link:
        xpath = "//button[not(@disabled) or @disabled='false']//p[contains(text(), 'Claim')]"
        if self.brute_click(xpath, 10, "click the 'Claim' button"):
            self.output(f"Step {self.step} - Claim was available and clicked.", 3)
            self.increase_step()
            success_text = "Claim attempted. "
            self.increase_step()

        # Check for 'Got it' message
        xpath = "//*[contains(text(), 'Got it')]"
        self.move_and_click(xpath, 10, True, "check for 'Got it' message (may not be present)", self.step, "clickable")
        #self.daily_reward()
        self.increase_step()

        # Calculate remaining time in hours
        try:
            hourly_profit = float(self.get_profit_hour(True))
            xpath = "//p[contains(., '/')]"
            elapsed = self.monitor_element(xpath, 10, "Get the timer bar")
            current, max_value = map(float, elapsed.split('/'))
            remaining_time_hours = (max_value - current) / hourly_profit
            theoretical_timer = remaining_time_hours * 60
        except Exception as e:
            print(f"An error occurred: {e} - Assigning 1 hour timer")
            theoretical_timer = 60

        # Get balance again
        self.get_balance(True)

        # Execute the JavaScript to detect the green dot
        js_code = """
        let shadowHost = document.querySelector('.css-4g6ai3');
        let shadowRoot = shadowHost.shadowRoot || shadowHost;
        let greenDot = shadowRoot.querySelector('circle[fill="#01DC01"]');
        return greenDot !== null;
        """

        # Get the daily reward if the dot is green
        if self.driver.execute_script(js_code):
            self.output(
                f"Step {self.step} - Starting the Daily Reward claim. "
                "Answer is uploaded manually, do not report this function "
                "as faulty if the code doesn't match!", 2
            )
            self.daily_reward()
        else:
            self.output(f"Step {self.step} - Skipping the daily rewards, it appears to have been claimed.", 3)

        # Calculate modified timer with random offset
        modified_timer = self.apply_random_offset(theoretical_timer)
        modified_timer_rounded = round(modified_timer, 1)
        self.output(f"STATUS: {success_text}Claim again in {modified_timer_rounded} minutes (originally {theoretical_timer:.1f})", 1)
        return int(modified_timer)

    def daily_reward(self):
        self.quit_driver()
        self.launch_iframe()
        xpath = "//div[contains(@class, 'css-4g6ai3')]"
        self.move_and_click(xpath, 30, True, "click on Daily Quests tab", self.step, "clickable")

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
            return

        self.increase_step()

        # Define the indices you can be careful, but not used_indices = []
        for index, digit in enumerate(content):
            xpath = f"//div[@class='css-k0i5go'][{digit}]"
            
            if self.move_and_click(xpath, 30, True, f"click on the path corresponding to digit {digit}", self.step, "clickable"):
                self.output(f"Step {self.step} - Clicked on element corresponding to digit {digit}.", 2)
            else:
                # Handle failure to click on an element
                self.output(f"Step {self.step} - Element corresponding to digit {digit} not found or not clickable.", 1)

        # Increment the step counter
        self.increase_step()

        # Check if alert is present
        invalid_puzzle_xpath = "//div[contains(text(), 'Invalid puzzle code')]/ancestor::div[contains(@class, 'chakra-alert')]"
        if self.move_and_click(invalid_puzzle_xpath, 30, True, "check if alert is present", self.step, "visible"):
            # Alert for invalid puzzle code is present
            self.output(f"Step {self.step} - Alert for invalid puzzle code is present.", 2)
        else:
            # Alert for invalid puzzle code is not present
            self.output(f"Step {self.step} - Alert for invalid puzzle code is not present.", 1)

        self.output(f"Step {self.step} - Completed daily reward sequence successfully.", 2)

        # add verification element for  "Invalid puzzle code"
        invalid_puzzle_xpath = "//div[contains(text(), 'Invalid puzzle code')]/ancestor::div[contains(@class, 'chakra-alert')]"
        if self.move_and_click(invalid_puzzle_xpath, 30, True, "check if alert is present", self.step, "visible"):
            self.output(f"Step {self.step} - Alert for invalid puzzle code is present.", 2)
        else:
            self.output(f"Step {self.step} - Alert for invalid puzzle code is not present.", 1)

        self.output(f"Step {self.step} - Completed daily reward sequence successfully.", 2)

    def get_balance(self, claimed=False):

        prefix = "After" if claimed else "Before"
        default_priority = 2 if claimed else 3

        # Dynamically adjust the log priority
        priority = max(self.settings['verboseLevel'], default_priority)

        # Construct the specific balance XPath
        balance_text = f'{prefix} BALANCE:' if claimed else f'{prefix} BALANCE:'
        balance_xpath = f"//h2[text()='Mana Balance']/following-sibling::h2[1]"

        try:
            element = self.strip_html_and_non_numeric(self.monitor_element(balance_xpath, 15, "get balance"))

            # Check if element is not None and process the balance
            if element:
                self.output(f"Step {self.step} - {balance_text} {element}", priority)

        except NoSuchElementException:
            self.output(f"Step {self.step} - Element containing '{prefix} Balance:' was not found.", priority)
        except Exception as e:
            self.output(f"Step {self.step} - An error occurred: {str(e)}", priority)  # Provide error as string for logging

        # Increment step function, assumed to handle next step logic
        self.increase_step()

    def get_profit_hour(self, claimed=False):
        prefix = "After" if claimed else "Before"
        default_priority = 2 if claimed else 3

        priority = max(self.settings['verboseLevel'], default_priority)

        # Construct the specific profit XPath
        profit_text = f'{prefix} PROFIT/HOUR:'
        profit_xpath = "//p[contains(text(), 'Mana per hour:')]/following-sibling::p[1]"

        try:
            element = self.strip_non_numeric(self.monitor_element(profit_xpath, 15, "profit per hour"))

            # Check if element is not None and process the profit
            if element:
                self.output(f"Step {self.step} - {profit_text} {element}", priority)
                return element
            return None
        except NoSuchElementException:
            self.output(f"Step {self.step} - Element containing '{prefix} Profit/Hour:' was not found.", priority)
        except Exception as e:
            self.output(f"Step {self.step} - An error occurred: {str(e)}", priority)  # Provide error as string for logging
        return None
        self.increase_step()

def main():
    claimer = SpellClaimer()
    claimer.run()

if __name__ == "__main__":
    main()