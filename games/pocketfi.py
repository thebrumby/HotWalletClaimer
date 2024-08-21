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

class PocketFiClaimer(Claimer):

    def initialize_settings(self):
        super().initialize_settings()
        self.script = "games/pocketfi.py"
        self.prefix = "Pocketfi:"
        self.url = "https://web.telegram.org/k/#@pocketfi_bot"
        self.pot_full = "Filled"
        self.pot_filling = "to fill"
        self.seed_phrase = None
        self.forceLocalProxy = False
        self.forceRequestUserAgent = False
        self.start_app_xpath = "//div[contains(@class, 'reply-markup-row')]//span[contains(., 'Mining') or contains(., 'Open PocketFi')]"

    def __init__(self):
        self.settings_file = "variables.txt"
        self.status_file_path = "status.txt"
        self.wallet_id = ""
        self.load_settings()
        self.random_offset = -60
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
        self.increase_step()

        time.sleep(15)
        xpath = "//div[contains(@class, 'popup-footer') and contains(@class, 'is-visible')]//button[text()='Go to mining']"
        button = self.move_and_click(xpath, 20, True, "click 'Go to mining' (may not be present)", self.step, "clickable")
        self.increase_step()

        self.get_balance(False)
        self.increase_step()

        wait_time_text = self.get_wait_time(self.step, "pre-claim") 
        if wait_time_text and isinstance(wait_time_text[0], int) and wait_time_text[0] > 330:
            self.output("STATUS: Looks like the pot isn't ready to claim yet. Let's come back in 30 minutes.", 1)
            return 30 

        self.output(f"Step {self.step} - the pre-claim timer shows {wait_time_text} minutes until burn.", 2)

        xpath = "//div[@class='absolute flex items-center justify-center flex-col text-white']/span[contains(text(), 'claim')]"
        attempts = 1
        clicked_it = False
        while attempts < 5:
            button = self.move_and_click(xpath, 30, False, "click claim", self.step, "visible")
            if button:
                self.driver.execute_script("arguments[0].click();", button)
            time.sleep(5)
            wait_time_text = self.get_wait_time(self.step, "mid-claim") 
            if wait_time_text and isinstance(wait_time_text[0], int) and wait_time_text[0] > 330:
                self.output(f"Step {self.step} - Looks like we made the claim on attempt {attempts}.", 3)
                clicked_it = True
                break
            else:
                self.output(f"Step {self.step} - Looks like we failed the claim on attempt {attempts}. Trying again.", 3)
                attempts += 1 
        self.increase_step()
        
        self.get_balance(True)
        self.increase_step()

        self.get_profit_hour(True)

        if clicked_it:
            self.output(f"STATUS: Successfully claimed after {attempts} attempts. Mine again in 4 hours.", 1)
            return 240
        else: 
            self.output(f"STATUS: Unable to click. CPU may not be fast enough. Let's come back in 1 hour.", 1)
        return 60

    def get_balance(self, claimed=False):
        prefix = "After" if claimed else "Before"
        default_priority = 2 if claimed else 3

        priority = max(self.settings['verboseLevel'], default_priority)

        balance_text = f'{prefix} BALANCE:' if claimed else f'{prefix} BALANCE:'
        balance_xpath = f"//span[@class='text-2xl font-bold']"

        try:
            first = self.move_and_click(balance_xpath, 30, False, "remove overlays", self.step, "visible")
            element = self.monitor_element(balance_xpath, 15, "get balance")
            if element:
                balance_part = element
                self.output(f"Step {self.step} - {balance_text} {balance_part}", priority)

        except NoSuchElementException:
            self.output(f"Step {self.step} - Element containing '{prefix} Balance:' was not found.", priority)
        except Exception as e:
            self.output(f"Step {self.step} - An error occurred: {str(e)}", priority) 

        self.increase_step()

    def get_wait_time(self, step_number="108", beforeAfter="pre-claim", max_attempts=1):

        def convert_to_minutes(time_str):
            if re.match(r"^\d{2}:\d{2}:\d{2}$", time_str):
                hours, minutes, seconds = map(int, time_str.split(':'))
                total_minutes = hours * 60 + minutes + seconds / 60
                return int(total_minutes)
            return time_str

        for attempt in range(1, max_attempts + 1):
            try:
                self.output(f"Step {self.step} - Get the wait time...", 3)
                xpath = "//p[contains(text(), 'burn in')]"
                elements = self.monitor_element(xpath, 10, "get claim timer")
                if elements:
                    match = re.search(r"burn in\s*(\d{2}:\d{2}:\d{2})", elements)
                    if match:
                        wait_time = match.group(1)
                        results = [convert_to_minutes(wait_time)]
                        return results
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
        profit_xpath = "//p[contains(., '$SWITCH')]//span[last()]"

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

def main():
    claimer = PocketFiClaimer()
    claimer.run()

if __name__ == "__main__":
    main()