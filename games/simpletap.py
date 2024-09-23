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

class SimpleTapClaimer(Claimer):

    def initialize_settings(self):
        super().initialize_settings()
        self.script = "games/simpletap.py"
        self.prefix = "SimpleTap:"
        self.url = "https://web.telegram.org/k/#@Simple_Tap_Bot"
        self.pot_full = "Filled"
        self.pot_filling = "Mining"
        self.seed_phrase = None
        self.forceLocalProxy = False
        self.forceRequestUserAgent = False
        self.start_app_xpath = "//div[contains(@class, 'new-message-wrapper')]//div[contains(text(), 'Start')]"

    def __init__(self):
        self.settings_file = "variables.txt"
        self.status_file_path = "status.txt"
        self.wallet_id = ""
        self.load_settings()
        self.random_offset = random.randint(self.settings['lowestClaimOffset'], self.settings['highestClaimOffset'])
        super().__init__()

    def launch_iframe(self):
        super().launch_iframe()

        # Open tab in main window
        self.driver.switch_to.default_content()

        iframe = self.driver.find_element(By.TAG_NAME, "iframe")
        iframe_url = iframe.get_attribute("src")
        
        # Check if 'tgWebAppPlatform=' exists in the iframe URL before replacing
        if "tgWebAppPlatform=" in iframe_url:
            # Replace both 'web' and 'weba' with the dynamic platform
            iframe_url = iframe_url.replace("tgWebAppPlatform=web", f"tgWebAppPlatform={self.default_platform}")
            iframe_url = iframe_url.replace("tgWebAppPlatform=weba", f"tgWebAppPlatform={self.default_platform}")
            self.output(f"Platform found and replaced with '{self.default_platform}'.", 2)
        else:
            self.output("No tgWebAppPlatform parameter found in the iframe URL.", 2)

        self.driver.execute_script(f"location.href = '{iframe_url}'")

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
            self.output(f"Step {self.step} - Failed to find or switch to the iframe within the timeout period.",1)

        except Exception as e:
            self.output(f"Step {self.step} - An error occurred: {e}",1)

    def full_claim(self):
        self.step = "100"
        self.launch_iframe()

        status_text = None  # Initialize status_text early

        try:
            # New button to join "Bump"
            original_window = self.driver.current_window_handle
            xpath = "//*[text()='Start']"
            self.move_and_click(xpath, 8, True, "click the 'Start' button (may not be present)", self.step, "clickable")

            # Switch back to the original window if a new one is opened
            new_window = [window for window in self.driver.window_handles if window != original_window]
            if new_window:
                self.driver.switch_to.window(original_window)
        except TimeoutException:
            if self.settings['debugIsOn']:
                self.output(f"Step {self.step} - 'Start' button not found or no new window opened.", 3)
        self.increase_step()

        opening_balance = self.get_balance(False)  # Capture starting balance

        # Collect the reward.
        xpath = "//div[contains(text(), 'Collect')]"
        self.move_and_click(xpath, 8, True, "click the 'Collect' button (may not be present)", self.step, "clickable")

        # Farming
        xpath = "//div[contains(text(), 'Start farming')]"
        button = self.move_and_click(xpath, 8, False, "click the 'Start farming' button", self.step, "clickable")
        if button: 
            button.click()
            status_text = "STATUS: Starting to farm now"
        else:
            status_text = "STATUS: Already farming"

        self.increase_step()

        closing_balance = self.get_balance(True)  # Capture closing balance

        try:
            # Convert both balances to float and calculate the balance change
            opening_balance = float(opening_balance)
            closing_balance = float(closing_balance)
            balance_increase = closing_balance - opening_balance

            # Update status_text based on balance change
            if balance_increase > 0:
                status_text += f". Balance increased by {balance_increase:.2f}"
            else:
                status_text += ". No balance increase"
        except ValueError:
            # Handle conversion errors
            self.output("Error converting balances to float", 3)

        wait_time = self.get_wait_time(self.step, "pre-claim") 

        # Take friends points
        xpath = "(//div[@class='appbar-tab'])[last()]"
        button = self.move_and_click(xpath, 8, False, "open 'Friends' tab", self.step, "clickable")
        if button: button.click()

        xpath = "//div[contains(@class, 'claim-button')]"
        button = self.move_and_click(xpath, 8, False, "click the 'Take Friends Points' button", self.step, "clickable")
        if button: 
            button.click()

            # Close the congratulations popup
            xpath = "//div[contains(@class, 'invite_claimed-button')]"
            button = self.move_and_click(xpath, 8, False, "exit the 'Congratulations' popup", self.step, "clickable")
            if button: button.click()
                
        self.increase_step()

        if wait_time is None:
            self.output(f"{status_text} - Failed to get wait time. Next try in 60 minutes", 3)
            return 60
        else:
            self.output(f"{status_text} - Next try in {self.show_time(wait_time)}.", 2)
            return max(wait_time, 60)

    def get_balance(self, claimed=False):

        def strip_html_and_non_numeric(text):
            """Remove HTML tags and keep only numeric characters and decimal points."""
            # Remove HTML tags
            clean = re.compile('<.*?>')
            text_without_html = clean.sub('', text)
            # Keep only numeric characters and decimal points
            numeric_text = re.sub(r'[^0-9.]', '', text_without_html)
            return numeric_text

        prefix = "After" if claimed else "Before"
        default_priority = 2 if claimed else 3

        # Dynamically adjust the log priority
        priority = max(self.settings['verboseLevel'], default_priority)

        # Construct the specific balance XPath
        balance_text = f'{prefix} BALANCE:' if claimed else f'{prefix} BALANCE:'
        balance_xpath = "//div[contains(@class, 'home_balance')]"

        try:
            element = self.monitor_element(balance_xpath)

            # Check if element is not None and process the balance
            if element:
                cleaned_balance = strip_html_and_non_numeric(element)  # Ensure we get the text of the element
                self.output(f"Step {self.step} - {balance_text} {cleaned_balance}", priority)
                return cleaned_balance

        except NoSuchElementException:
            self.output(f"Step {self.step} - Element containing '{prefix} Balance:' was not found.", priority)
        except Exception as e:
            self.output(f"Step {self.step} - An error occurred: {str(e)}", priority)  # Provide error as string for logging

        # Increment step function, assumed to handle next step logic
        self.increase_step()

    def get_wait_time(self, step_number="108", beforeAfter="pre-claim"):
        try:

            self.output(f"Step {self.step} - check if the timer is elapsing...", 3)

            xpath = "//div[contains(@class, 'header_timer')]"
            wait_time = self.extract_time(self.strip_html_tags(self.monitor_element(xpath, 15)))

            self.output(f"Step {self.step} - The wait time is {wait_time} minutes.")

            return wait_time          

        except Exception as e:
            self.output(f"Step {self.step} - An error occurred: {e}", 3)
            if self.settings['debugIsOn']:
                screenshot_path = f"{self.screenshots_path}/{self.step}_get_wait_time_error.png"
                self.driver.save_screenshot(screenshot_path)
                self.output(f"Screenshot saved to {screenshot_path}", 3)

            return None

    def extract_time(self, text):
        time_parts = text.split(':')
        if len(time_parts) == 3:
            try:
                hours = int(time_parts[0].strip())
                minutes = int(time_parts[1].strip())
                return hours * 60 + minutes
            except ValueError:
                return False
        return False
    
    def strip_html_tags(self, text):
        clean = re.compile('<.*?>')
        text_without_html = re.sub(clean, '', text)
        text_cleaned = re.sub(r'[^0-9:.]', '', text_without_html)
        return text_cleaned

    def show_time(self, time):
        hours = int(time / 60)
        minutes = time % 60
        if hours > 0:
            return f"{hours} hours and {minutes} minutes"
        return f"{minutes} minutes"

def main():
    claimer = SimpleTapClaimer()
    claimer.run()

if __name__ == "__main__":
    main()
