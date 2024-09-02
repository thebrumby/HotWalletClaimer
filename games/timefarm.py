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
from claimer import Claimer
import requests
from datetime import date
import urllib.request

class TimeFarmClaimer(Claimer):

    def initialize_settings(self):
        super().initialize_settings()
        self.script = "games/timefarm.py"
        self.prefix = "TimeFarm:"
        self.url = "https://web.telegram.org/k/#@TimeFarmCryptoBot"
        self.pot_full = "Filled"
        self.pot_filling = "to fill"
        self.seed_phrase = None
        self.forceLocalProxy = False
        self.forceRequestUserAgent = False
        self.start_app_xpath = "//span[contains(text(), 'Open App')]"

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

            cookies_path = f"{self.session_path}/cookies.json"
            cookies = self.driver.get_cookies()
            with open(cookies_path, 'w') as file:
                json.dump(cookies, file)

        except TimeoutException:
            self.output(f"Step {self.step} - Failed to find or switch to the iframe within the timeout period.",1)

        except Exception as e:
            self.output(f"Step {self.step} - An error occurred: {e}",1)

    def full_claim(self):

        self.step = "100"

        self.launch_iframe()
        xpath = "//div[@class='app-container']//div[@class='btn-text' and contains(., 'Claim')]"
        start_present = self.move_and_click(xpath, 8, False, "make splash screen 'Claim' (may not be present)", self.step, "clickable")
        self.increase_step()

        self.get_balance(False)
        self.increase_step()

        xpath = "//div[@class='farming-button-block'][.//span[text()='Start']]"
        start_present = self.move_and_click(xpath, 10, True, "click the 'Start' button (may not be present)", self.step, "clickable")
        self.increase_step()

        xpath = "//div[@class='farming-button-block'][.//span[text()='Claim']]"
        success = self.move_and_click(xpath, 20, True, "look for the claim button (may not be present)", self.step, "clickable")
        self.increase_step()
        if success:
            self.output(f"STATUS: We appear to have correctly clicked the claim button.",1)
        else:
            self.output(f"STATUS: The Claim button wasn't clickable on this occassion.",1)

        xpath = "//div[@class='farming-button-block'][.//span[text()='Start']]"
        self.move_and_click(xpath, 20, True, "click the 'Start' button (may not be present)", self.step, "clickable")

        remaining_time = self.get_wait_time()
        self.increase_step()
        self.get_balance(True)
        self.stake_coins()
        self.claim_frens()
        self.claim_oracle()
        if isinstance(remaining_time, (int, float)):
            return self.apply_random_offset(remaining_time)
        else:
            return 120
        
    def claim_frens(self):

        self.quit_driver()
        self.launch_iframe()

        # Navigate to the 'Frens' tab
        FREN_TAB_XPATH = "//div[@class='tab-title' and text()='Frens']"
        if not self.move_and_click(FREN_TAB_XPATH, 20, True, "Switch to the 'Frens' tab", self.step, "clickable"):
            self.increase_step()
            return
        self.increase_step()

        # Click on the 'Claim' button        
        CLAIM_BUTTON_XPATH = "//div[@class='btn-text' and text()='Claim']"
        self.move_and_click(CLAIM_BUTTON_XPATH, 20, True, "Click on the 'Claim' button", self.step, "clickable")
        self.increase_step()
            

    def navigate_to_date_input(self):
        # Step 1: Navigate to the 'Earn' tab
        EARN_TAB_XPATH = "//div[@class='tab-title'][contains(., 'Earn')]"
        if not self.move_and_click(EARN_TAB_XPATH, 20, True, "Switch to the 'Earn' tab", self.step, "clickable"):
            self.increase_step()
            return False

        self.increase_step()

        # Step 2: Click on the 'Oracle of Time' button
        ORACLE_BUTTON_XPATH = "//div[contains(text(), 'Oracle of Time')]"
        if not self.move_and_click(ORACLE_BUTTON_XPATH, 20, True, "Click on the 'Oracle of Time' button", self.step, "clickable"):
            self.increase_step()
            return False

        # Step 3: Check if it's already been answered
        CHECK_XPATH = "//div[contains(text(), 'You have already answered')]"
        if self.move_and_click(CHECK_XPATH, 10, True, "check if already answered", self.step, "clickable"):
            self.increase_step()
            self.output(f"Step {self.step} - You have already answered today\'s Oracle of Time", 2)
            return False

        self.increase_step()
        return True

    def claim_oracle(self):
        # Step 1-3: Navigate to the correct place to input the date
        if not self.navigate_to_date_input():
            return

        # Step 4: Fetch the content from the GitHub file using urllib
        url = "https://raw.githubusercontent.com/thebrumby/HotWalletClaimer/main/extras/timefarmdaily"
        try:
            with urllib.request.urlopen(url) as response:
                content = response.read().decode('utf-8').strip()
            self.output(f"Step {self.step} - Fetched content from GitHub: {content}", 3)
        except Exception as e:
            self.output(f"Step {self.step} - Failed to fetch Oracle of Time from GitHub: {str(e)}", 2)
            return

        self.increase_step()

        # Step 4: Process the content as a date
        content = self.strip_non_numeric(content)
        if len(content) == 8 and content.isdigit():
            day = content[:2]
            month = content[2:4]
            year = content[4:]
            date_string = f"{day}{month}{year}"  # Format as 'DDMMYYYY'
            self.output(f"Step {self.step} - Date extracted: {day}/{month}/{year}", 3)
        else:
            self.output(f"Step {self.step} - Content is not a valid 8-digit date: {content}", 2)
            return

        self.increase_step()

        # Step 5: Try entering the date in 'dd/mm/yyyy' format first
        if not self.enter_date(day, month, year, date_string, "dd/mm/yyyy"):
            self.output(f"Step {self.step} - dd/mm/yyyy format failed. Retrying with mm/dd/yyyy.", 3)
            self.quit_driver()  # Quit the driver
            time.sleep(5)  # Wait a bit before relaunching
            self.launch_iframe()  # Relaunch the driver

            # Re-navigate to the correct place
            if not self.navigate_to_date_input():
                return

            # Retry entering the date in 'mm/dd/yyyy' format
            if not self.enter_date(day, month, year, date_string, "mm/dd/yyyy"):
                self.output(f"Step {self.step} - mm/dd/yyyy format also failed. Exiting.", 2)
                return

        self.increase_step()

        # Step 6: Navigate to the 'checkzedate' tab
        CHECKDATE_XPATH = "//div[text()='Check the date']"
        self.move_and_click(CHECKDATE_XPATH, 10, True, "check if date correct", self.step, "clickable")

        TRYAGAIN_XPATH = "//div[text()='Try again']"
        failure = self.move_and_click(TRYAGAIN_XPATH, 10, True, "check if completion error", self.step, "clickable")
        if not failure:
            CLAIM_XPATH = "//div[contains(text(),'Claim')]"
            self.move_and_click(CLAIM_XPATH, 10, True, "claim after success", self.step, "clickable")
            self.output(f"Step {self.step} - Oracle of Time verified as complete.", 2)
        else:
            self.output(f"Step {self.step} - The oracle of time date was wrong for the current puzzle.", 3)

    def enter_date(self, day, month, year, date_string, date_format):
        DATE_XPATH = "//input[@name='trip-start']"
        TRYAGAIN_XPATH = "//div[text()='Try again']"
        CHECKDATE_XPATH = "//div[text()='Check the date']"
    
        try:
            trip_start_field = self.move_and_click(DATE_XPATH, 10, True, "click on date picker", self.step, "clickable")
            trip_start_field.clear()  # Clear any pre-existing value in the field
            self.increase_step()

            if date_format == "dd/mm/yyyy":
                # Send day first
                self.output(f"Step {self.step} - Trying format dd/mm/yyyy", 3)
                self.output(f"Step {self.step} - Sending day: {day}", 3)
                trip_start_field.send_keys(day)
                time.sleep(1)
                self.output(f"Step {self.step} - Sending month: {month}", 3)
                trip_start_field.send_keys(month)
            else:
                # Send month first
                self.output(f"Step {self.step} - Trying format mm/dd/yyyy", 3)
                self.output(f"Step {self.step} - Sending month: {month}", 3)
                trip_start_field.send_keys(month)
                time.sleep(1)
                self.output(f"Step {self.step} - Sending day: {day}", 3)
                trip_start_field.send_keys(day)

            # Send the year
            time.sleep(1)
            self.output(f"Step {self.step} - Sending year: {year}", 3)
            trip_start_field.send_keys(year)
        
            # Confirm the date input
            time.sleep(2)
            self.move_and_click(CHECKDATE_XPATH, 10, True, "confirm date", self.step, "visible")
            self.output(f"Step {self.step} - Date submitted successfully in format {date_format}: {date_string[:2]}/{date_string[2:4]}/{date_string[4:]}", 3)

            # Check if the "Try again" button is present, indicating failure
            if self.move_and_click(TRYAGAIN_XPATH, 10, True, "check if answer was wrong", self.step, "visible"):
                self.output(f"Step {self.step} - 'Try again' button detected. Date format {date_format} was incorrect.", 2)
                return False  # Trigger retry

            return True  # Success

        except Exception as e:
            self.output(f"Step {self.step} - Error submitting the date: {str(e)}", 2)
            return False  # Failure


    def get_balance(self, claimed=False):

        prefix = "After" if claimed else "Before"
        default_priority = 2 if claimed else 3

        # Dynamically adjust the log priority
        priority = max(self.settings['verboseLevel'], default_priority)

        # Construct the specific balance XPath
        balance_text = f'{prefix} BALANCE:' if claimed else f'{prefix} BALANCE:'
        balance_xpath = f"//div[@class='balance']"
        try:
            balance_part = self.monitor_element(balance_xpath)
            # Strip any HTML tags and unwanted characters
            balance_part = "$" + self.strip_html_tags(balance_part)
            # Check if element is not None and process the balance
            self.output(f"Step {self.step} - {balance_text} {balance_part}", priority)

        except NoSuchElementException:
            self.output(f"Step {self.step} - Element containing '{prefix} Balance:' was not found.", priority)
        except Exception as e:
            self.output(f"Step {self.step} - An error occurred: {str(e)}", priority)  # Provide error as string for logging

    def strip_html_tags(self, text):
        """Remove HTML tags, newlines, and excess spaces from a given string."""
        clean = re.compile('<.*?>')
        text_without_html = re.sub(clean, '', text)
        # Remove any non-numeric and non-colon characters, but keep spaces for now
        text_cleaned = re.sub(r'[^0-9: ]', '', text_without_html)
        # Remove spaces
        text_cleaned = re.sub(r'\s+', '', text_cleaned)
        return text_cleaned

    def extract_time(self, text):
        """Extract time from the cleaned text and convert to minutes."""
        time_parts = text.split(':')
        if len(time_parts) == 3:
            try:
                hours = int(time_parts[0].strip())
                minutes = int(time_parts[1].strip())
                # We assume seconds are not needed for minute calculation
                # seconds = int(time_parts[2].strip())
                return hours * 60 + minutes
            except ValueError:
                return "Unknown"
        return "Unknown"

    def get_wait_time(self, step_number="108", beforeAfter="pre-claim", max_attempts=1):

        for attempt in range(1, max_attempts + 1):
            try:
                self.output(f"Step {self.step} - check if the timer is elapsing...", 3)
                xpath = "//table[@class='scroller-table']"
                pot_full_value = self.monitor_element(xpath, 15)
                
                # Strip any HTML tags and unwanted characters
                pot_full_value = self.strip_html_tags(pot_full_value)
                
                # Convert to minutes
                wait_time_in_minutes = self.extract_time(pot_full_value)
                return wait_time_in_minutes
            except Exception as e:
                self.output(f"Step {self.step} - An error occurred on attempt {attempt}: {e}", 3)
                return "Unknown"

        # If all attempts fail         
        return "Unknown"

    def stake_coins(self):
        pass

def main():
    claimer = TimeFarmClaimer()
    claimer.run()

if __name__ == "__main__":
    main()