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

class TimeFarmClaimer(Claimer):

    def __init__(self):

        # Define sessions and settings files
        self.settings_file = "variables.txt"
        self.status_file_path = "status.txt"
        self.load_settings()
        self.random_offset = random.randint(max(self.settings['lowestClaimOffset'],0), max(self.settings['highestClaimOffset'],0))
        self.script = "games/time-farm.py"
        self.prefix = "Time-Farm:"
        self.url = "https://web.telegram.org/k/#@TimeFarmCryptoBot"
        self.pot_full = "Filled"
        self.pot_filling = "to fill"
        self.seed_phrase = None
        self.forceLocalProxy = False
        self.forceRequestUserAgent = False

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

        def apply_random_offset(unmodifiedTimer):
            if self.settings['lowestClaimOffset'] <= self.settings['highestClaimOffset']:
                self.random_offset = random.randint(max(self.settings['lowestClaimOffset'],0), max(self.settings['highestClaimOffset'],0))
                modifiedTimer = unmodifiedTimer + self.random_offset
                self.output(f"Step {self.step} - Random offset applied to the wait timer of: {self.random_offset} minutes.", 2)
                return modifiedTimer

        self.launch_iframe()

        self.get_balance(False)
        self.increase_step()

        xpath = "//div[@class='farming-button-block'][.//span[text()='Start']]"
        start_present = self.move_and_click(xpath, 8, False, "click the 'Start' button (may not be present)", self.step, "clickable")
        if start_present:
            self.click_element(xpath, 20)
        self.increase_step()

        remaining_time = self.get_wait_time()
        self.increase_step()
        
        if isinstance(remaining_time, (int, float)):
            remaining_time = apply_random_offset(remaining_time)
            self.output(f"STATUS: We still have {remaining_time} minutes left to wait - sleeping.", 1)
            return remaining_time

        xpath = "//div[@class='farming-button-block'][.//span[text()='Claim']]"
        self.move_and_click(xpath, 20, False, "look for the claim button.", self.step, "visible")
        success = self.click_element(xpath, 20)
        if success:
            self.increase_step()
            self.output(f"STATUS: We appear to have correctly clicked the claim button.",1)
            xpath = "//div[@class='farming-button-block'][.//span[text()='Start']]"
            start_present = self.move_and_click(xpath, 20, False, "click the 'Start' button", self.step, "clickable")
            if start_present:
                self.click_element(xpath, 20)
                self.increase_step()
            remaining_time = self.get_wait_time()
            self.increase_step()
            self.get_balance(True)
            return apply_random_offset(remaining_time)
        else:
            self.output(f"STATUS: The claim button wasn't clickable on this occassion.",1)
            return 60
            
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
                self.output (f"Step {self.step} - The remaining minutes in the wait timer were {wait_time_in_minutes}",3)
                return wait_time_in_minutes
            except Exception as e:
                self.output(f"Step {self.step} - An error occurred on attempt {attempt}: {e}", 3)
                return "Unknown"

        # If all attempts fail         
        return "Unknown"

    def find_working_link(self, old_step):

        self.output(f"Step {self.step} - Attempting to open a link for the app...",2)

        start_app_xpath = "//span[contains(text(), 'Open App')]"
        try:
            start_app_buttons = WebDriverWait(self.driver, 5).until(EC.presence_of_all_elements_located((By.XPATH, start_app_xpath)))
            clicked = False

            for button in reversed(start_app_buttons):
                actions = ActionChains(self.driver)
                actions.move_to_element(button).pause(0.2)
                try:
                    if self.settings['debugIsOn']:
                        self.driver.save_screenshot(f"{self.screenshots_path}/{self.step} - Find working link.png".format(self.screenshots_path))
                    actions.perform()
                    self.driver.execute_script("arguments[0].click();", button)
                    clicked = True
                    break
                except StaleElementReferenceException:
                    continue
                except ElementClickInterceptedException:
                    continue

            if not clicked:
                self.output(f"Step {self.step} - None of the 'Open Wallet' buttons were clickable.\n",1)
                if self.settings['debugIsOn']:
                    screenshot_path = f"{self.screenshots_path}/{self.step}-no-clickable-button.png"
                    self.driver.save_screenshot(screenshot_path)
                return False
            else:
                self.output(f"Step {self.step} - Successfully able to open a link for the app..\n",3)
                if self.settings['debugIsOn']:
                    screenshot_path = f"{self.screenshots_path}/{self.step}-app-opened.png"
                    self.driver.save_screenshot(screenshot_path)
                return True

        except TimeoutException:
            self.output(f"Step {self.step} - Failed to find the 'Open Wallet' button within the expected timeframe.\n",1)
            if self.settings['debugIsOn']:
                screenshot_path = f"{self.screenshots_path}/{self.step}-timeout-finding-button.png"
                self.driver.save_screenshot(screenshot_path)
            return False
        except Exception as e:
            self.output(f"Step {self.step} - An error occurred while trying to open the app: {e}\n",1)
            if self.settings['debugIsOn']:
                screenshot_path = f"{self.screenshots_path}/{self.step}-unexpected-error-opening-app.png"
                self.driver.save_screenshot(screenshot_path)
            return False

    def find_claim_link(self, old_step):

        self.output(f"Step {self.step} - Attempting to open a link for the app...", 2)

        # Updated to use a more generic CSS selector
        start_app_css_selector = ".farming-buttons-wrapper .kit-button"
        try:
            # Fetching all spans inside buttons
            start_app_buttons = WebDriverWait(self.driver, 5).until(
                EC.presence_of_all_elements_located((By.CSS_SELECTOR, start_app_css_selector))
            )
            # Filter buttons to find the one with specific text
            start_app_buttons = [btn for btn in start_app_buttons if 'Launch Blum' in btn.text]

            clicked = False

            for button in reversed(start_app_buttons):
                actions = ActionChains(self.driver)
                actions.move_to_element(button).pause(0.2)
                try:
                    if self.settings['debugIsOn']:
                        self.driver.save_screenshot(f"{self.screenshots_path}/{self.step} - Find working link.png")
                    actions.perform()
                    self.driver.execute_script("arguments[0].click();", button)
                    clicked = True
                    break
                except StaleElementReferenceException:
                    continue
                except ElementClickInterceptedException:
                    continue

            if not clicked:
                self.output(f"Step {self.step} - None of the 'Launch Blum' buttons were clickable.\n", 1)
                if self.settings['debugIsOn']:
                    screenshot_path = f"{self.screenshots_path}/{self.step}-no-clickable-button.png"
                    self.driver.save_screenshot(screenshot_path)
                return False
            else:
                self.output(f"Step {self.step} - Successfully able to open a link for the app..\n", 3)
                if self.settings['debugIsOn']:
                    screenshot_path = f"{self.screenshots_path}/{self.step}-app-opened.png"
                    self.driver.save_screenshot(screenshot_path)
                return True

        except TimeoutException:
            self.output(f"Step {self.step} - Failed to find the 'Launch Blum' button within the expected timeframe.\n", 1)
            if self.settings['debugIsOn']:
                screenshot_path = f"{self.screenshots_path}/{self.step}-timeout-finding-button.png"
                self.driver.save_screenshot(screenshot_path)
            return False
        except Exception as e:
            self.output(f"Step {self.step} - An error occurred while trying to open the app: {e}\n", 1)
            if self.settings['debugIsOn']:
                screenshot_path = f"{self.screenshots_path}/{self.step}-unexpected-error-opening-app.png"
                self.driver.save_screenshot(screenshot_path)
            return False

def main():
    claimer = TimeFarmClaimer()
    claimer.run()

if __name__ == "__main__":
    main()
