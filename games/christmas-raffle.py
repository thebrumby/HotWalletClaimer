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
        self.script = "games/christmas-raffle.py"
        self.prefix = "Xmas-Raffle:"
        self.url = "https://web.telegram.org/k/#@tapps_bot"
        self.pot_full = "Filled"
        self.pot_filling = "to fill"
        self.seed_phrase = None
        self.forceLocalProxy = False
        self.forceRequestUserAgent = False
        self.allow_early_claim = True
        self.start_app_xpath = "//div[@class='new-message-bot-commands-view' and contains(text(),'Apps Center')]"

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
        # before_balance = self.get_balance(False)

        # Brute force the claim to collect all '%' and then spin the wheel:
        xpath = "//button[contains(text(),'Next')]"
        if self.brute_click(xpath, 12, "click the 'Next' button(s)"):
            self.output(f"Step {self.step} - Next button(s) were available and clicked.", 3)
            self.increase_step()
            
            xpath = "//button[contains(text(),'Done')]"
            self.brute_click(xpath, 12, "click the 'Done' button")

        # Check how many days in the streak
        self.get_balance(False)
        self.increase_step()

        # Get the wait timer if present
        remaining_wait_time = self.get_wait_time(self.step, "post-claim")
        self.increase_step()
            
        if not remaining_wait_time:
            self.output(f"STATUS: Claim not attempted; need to wait until the next daily reward chance is available.", 1)
            return 60 * 8 
            
        xpath = "//h1[contains(text(),'Complete day')]"
        self.move_and_click(xpath, 20, True, "check for daily reward", self.step, "clickable")
        self.increase_step()
        
        xpath = "//span[contains(@class, 'styles_button') and text()='Open']"
        self.move_and_click(xpath, 20, True, "click 'open' button", self.step, "clickable")
        self.increase_step()
        
        # Now let's move to and JS click the "Cancel" Button
        xpath = "//button[contains(@class, 'popup-button') and contains(., 'Cancel')]"
        button = self.move_and_click(xpath, 8, True, "click the 'Cancel' button", self.step, "clickable")
        self.increase_step()
        
        self.output(f"STATUS: Claim attempted; need to wait until the next daily reward chance is available.", 1)
        return 60 * 8 

    def get_balance(self, claimed=False):
        prefix = "After #days streak" if claimed else "Before #days streak"
        default_priority = 2 if claimed else 3
    
        # Dynamically adjust the log priority
        priority = max(self.settings.get('verboseLevel', default_priority), default_priority)
    
        # Construct text based on before/after
        balance_text = f'{prefix} BALANCE:'
        balance_xpath = "//h1[contains(text(),'Complete day')]"
    
        try:
            # Monitor the element and ensure it returns a valid string
            element = self.monitor_element(balance_xpath, 15, "get balance")
            if not element:
                self.output(f"Step {self.step} - {balance_text} element not found.", priority)
                return None
    
            # Strip non-numeric content and ensure it's valid
            stripped_element = self.strip_html_and_non_numeric(element)
            if stripped_element is None or not stripped_element.isdigit():
                self.output(f"Step {self.step} - {balance_text} element found but not numeric: '{element}'", priority)
                return None
    
            # Convert to integer and log the balance
            balance_float = int(stripped_element)
            self.output(f"Step {self.step} - {balance_text} {balance_float}", priority)
            return balance_float
    
        except Exception as e:
            # Handle general exceptions with clear error messages
            self.output(f"Step {self.step} - An error occurred while getting balance: {str(e)}", priority)
            return None
    
        finally:
            # Ensure step increment happens even if there’s an issue
            self.increase_step()
    
    def get_wait_time(self, step_number="108", beforeAfter="pre-claim"):
        try:
            self.output(f"Step {self.step} - Get the wait time...", 3)
    
            # XPath to find the span element with the specific class
            xpath = "//span[contains(@class, 'styles_footNote__A+ki8') and contains(text(), ':')]"
            wait_time_text = self.monitor_element(xpath, 10, "claim timer")
    
            # Check if `wait_time_text` is valid
            if not wait_time_text:
                self.output(f"Step {self.step} - No wait time text found.", 3)
                return False
    
            wait_time_text = wait_time_text.strip()
            self.output(f"Step {self.step} - Extracted wait time text: '{wait_time_text}'", 3)
    
            # Regular expression to match hh:mm:ss or mm:ss format
            pattern_hh_mm_ss = r'^(\d{1,2}):(\d{2}):(\d{2})$'
            pattern_mm_ss = r'^(\d{1,2}):(\d{2})$'
    
            if re.match(pattern_hh_mm_ss, wait_time_text):
                hours, minutes, seconds = map(int, re.findall(r'\d+', wait_time_text))
                total_minutes = hours * 60 + minutes
                self.output(f"Step {self.step} - Total wait time in minutes: {total_minutes}", 3)
                return total_minutes
            elif re.match(pattern_mm_ss, wait_time_text):
                minutes, seconds = map(int, re.findall(r'\d+', wait_time_text))
                self.output(f"Step {self.step} - Total wait time in minutes: {minutes}", 3)
                return minutes
            else:
                self.output(f"Step {self.step} - Wait time pattern not matched: '{wait_time_text}'", 3)
                return False
    
        except Exception as e:
            self.output(f"Step {self.step} - An error occurred while getting wait time: {str(e)}", 3)
            return False

def main():
    claimer = SpellClaimer()
    claimer.run()

if __name__ == "__main__":
    main()
