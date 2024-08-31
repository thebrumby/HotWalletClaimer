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

class TabizooClaimer(Claimer):

    def initialize_settings(self):
        super().initialize_settings()
        self.script = "games/tabizoo.py"
        self.prefix = "TabiZoo:"
        self.url = "https://web.telegram.org/k/#@tabizoobot"
        self.pot_full = "Filled"
        self.pot_filling = "to fill"
        self.box_claim = "Never."
        self.seed_phrase = None
        self.forceLocalProxy = False
        self.forceRequestUserAgent = False
        self.allow_early_claim = False
        self.start_app_xpath = "//div[contains(@class, 'new-message-bot-commands') and .//div[text()='Start']]"

    def __init__(self):
        self.settings_file = "variables.txt"
        self.status_file_path = "status.txt"
        self.wallet_id = ""
        self.load_settings()  # Load settings before initializing other attributes
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
            self.check_initial_screens()
            self.increase_step()
            self.set_cookies()

        except TimeoutException:
            self.output(f"Step {self.step} - Failed to find or switch to the iframe within the timeout period.", 1)

        except Exception as e:
            self.output(f"Step {self.step} - An error occurred: {e}", 1)

    def full_claim(self):
        self.step = "100"

        # Open the driver and proceed to the game.
        self.launch_iframe()
        self.increase_step()

        # Check the Daily rewards.
        self.check_initial_screens()
        self.increase_step()

        # Check the Daily rewards.
        self.click_daily_reward()
        self.increase_step()

        self.get_balance(False)
        self.increase_step()

        xpath = "//div[contains(text(), 'Claim')]"
        success = self.brute_click(xpath, 10, "click the 'Claim' button")
        if success:
            self.output(f"Step {self.step} - Main reward claimed.", 1)
        balance = self.get_balance(True)
        self.increase_step()

        self.get_profit_hour(True)

        try:
            wait_time_text = self.get_wait_time(self.step, "post-claim")
            self.attempt_upgrade(balance)

            if wait_time_text:
                matches = re.findall(r'(\d+)([hm])', wait_time_text)
                remaining_wait_time = sum(int(value) * (60 if unit == 'h' else 1) for value, unit in matches)
                remaining_wait_time = self.apply_random_offset(remaining_wait_time)
                self.output(f"STATUS: Considering {wait_time_text}, we'll go back to sleep for {remaining_wait_time} minutes.", 1)
                return remaining_wait_time

        except Exception as e:
            self.output(f"Step {self.step} - An unexpected error occurred: {e}", 1)
            return 60

        self.output(f"STATUS: We seemed to have reached the end without confirming the action!", 1)
        return 60
        
    def click_daily_reward(self):
        # Check the Daily rewards.
        xpath = "//img[contains(@src, 'checkin_icon')]/following-sibling::div[contains(@class, 'bg-[#FF5C01]')]"
        success = self.move_and_click(xpath, 10, False, "check if the daily reward can be claimed (may not be present)", self.step, "clickable")
        if not success:
            self.output(f"Step {self.step} - The daily reward appears to have already been claimed.", 2)
            self.increase_step()
            return
        xpath = "//div[contains(text(), 'Task')]"
        success = self.brute_click(xpath, 10, "click the 'Check Login' tab")
        self.increase_step()

        xpath = "//h4[contains(text(), 'Daily Reward')]"
        success = self.brute_click(xpath, 10, "click the 'Daily Reward' button")
        self.increase_step()

        xpath = "//div[contains(text(), 'Claim')]"
        success = self.brute_click(xpath, 10, "claim the 'Daily Reward'")
        self.increase_step()

        xpath = "//div[contains(text(), 'Come Back Tomorrow')]"
        success = self.move_and_click(xpath, 10, False, "check for 'Come Back Tomorrow'", self.step, "visible")
        self.increase_step()

        if not success:
            self.output(f"Step {self.step}: It seems the sequence to claim the daily reward failed.", 2)
            return

        self.output(f"STATUS: Successfully claimed the daily reward.", 2)

        self.quit_driver()
        self.launch_iframe()

    def check_initial_screens(self):
        # First 'Next Step' button
        xpath = "(//div[contains(text(), 'Next Step')])[1]"
        if not self.move_and_click(xpath, 10, True, "click the 1st 'Next Step' button", self.step, "clickable"):
            self.output(f"Step {self.step} - You have already cleared the initial screens.", 2)
            self.increase_step()
            return True

        self.increase_step()
        self.output(f"Step {self.step} - Tabizoo is still at the initial screens.", 1)
        self.output(f"STATUS: Navigate to make your initial claim in GUI.", 1)
        sys.exit()
        

    def get_balance(self, claimed=False):
        prefix = "After" if claimed else "Before"
        default_priority = 2 if claimed else 3

        priority = max(self.settings['verboseLevel'], default_priority)

        balance_text = f'{prefix} BALANCE:' if claimed else f'{prefix} BALANCE:'
        balance_xpath = f"//img[contains(@src, 'coin2')]/following-sibling::span"

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
                xpath = "//div[contains(text(), 'h') and contains(text(), ':') and contains(text(), 'm')]"
                elements = self.monitor_element(xpath, 10, "get claim timer")
                if elements:
                    return elements
                return False
            except Exception as e:
                self.output(f"Step {self.step} - An error occurred on attempt {attempt}: {e}", 3)
                return False

        return False

    def get_profit_hour(self, claimed=False):
        prefix = "After" if claimed else "Before"
        default_priority = 2 if claimed else 3

        priority = max(self.settings['verboseLevel'], default_priority)

        # Construct the specific profit XPath
        profit_text = f'{prefix} PROFIT/HOUR:'
        profit_xpath = "//label[text()='Mining Rate']/following-sibling::p//span[1]"

        try:
            element = self.strip_non_numeric(self.monitor_element(profit_xpath, 15, "profit per hour"))

            # Check if element is not None and process the profit
            if element:
                self.output(f"Step {self.step} - {profit_text} {element}", priority)

        except NoSuchElementException:
            self.output(f"Step {self.step} - Element containing '{prefix} Profit/Hour:' was not found.", priority)
        except Exception as e:
            self.output(f"Step {self.step} - An error occurred: {str(e)}", priority)  # Provide error as string for logging
        
        self.increase_step()

    def attempt_upgrade(self):
        pass

def main():
    claimer = TabizooClaimer()
    claimer.run()

if __name__ == "__main__":
    main()