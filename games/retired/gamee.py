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

class GameeClaimer(Claimer):

    def initialize_settings(self):
        super().initialize_settings()
        self.script = "games/gamee.py"
        self.prefix = "Gamee:"
        self.url = "https://web.telegram.org/k/#@gamee"
        self.pot_full = "Filled"
        self.pot_filling = "Mining"
        self.seed_phrase = None
        self.forceLocalProxy = True
        self.forceRequestUserAgent = False
        self.start_app_xpath = "//div[text()='Open app']"

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

        clicked_it = False

        status_text = ""

        # Attempt to click the 'Start mining' button
        xpath = "//button[span[contains(text(), 'Start mining')]]"
        clicked = self.move_and_click(xpath, 8, True, "click the 'Start mining' button", self.step, "clickable")
        if clicked:
            self.output(f"Step {self.step} - Successfully clicked 'Start mining' button.", 3)
            status_text = "Started MINING"
        else:
            # Attempt to click the 'Claim & start' button
            xpath = "//button[span[contains(text(), 'Claim & start')]]"
            clicked = self.move_and_click(xpath, 8, True, "click the 'Claim & start' button", self.step, "clickable")
            if clicked:
                self.output(f"Step {self.step} - Successfully clicked 'Claim & Start' button.", 3)
                status_text = "Started MINING"
            else:
                # Check if currently mining
                xpath = "//p[contains(text(), 'to claim')]"
                element_present = self.move_and_click(xpath, 8, False, "check if currently mining", self.step, "clickable")
                if element_present:
                    self.output(f"Step {self.step} - Currently mining: YES.", 3)
                    status_text = "Currently mining"
                else:
                    self.output(f"Step {self.step} - MINING button NOT found.", 3)
                    status_text = "MINING button NOT found"

        self.increase_step()

        wait_time = self.get_wait_time(self.step, "pre-claim")
        self.get_balance(True)


        xpath = "//div[contains(@href, 'wheel')]"
        self.move_and_click(xpath, 10, True, "click the 'Spin TAB'", self.step, "clickable")
        xpath = "//button[.//text()[contains(., 'available')]]"
        success = self.move_and_click(xpath, 10, True, "spin the wheel", self.step, "clickable")
        if success:
            status_text += ". Wheel bonus collected"

        if wait_time is None:
            self.output(f"STATUS: {status_text} - Failed to get wait time. Next try in 60 minutes", 2)
            return 60
        else:
            remaining_time = self.apply_random_offset(wait_time)
            self.output(f"STATUS: {status_text} - Next try in {self.show_time(remaining_time)}.", 1)
            return wait_time

    def get_balance(self, claimed=False):
        prefix = "After" if claimed else "Before"
        default_priority = 2 if claimed else 3

        # Dynamically adjust the log priority
        priority = max(self.settings['verboseLevel'], default_priority)

        # Construct text based on before/after
        balance_text = f'{prefix} BALANCE:' if claimed else f'{prefix} BALANCE:'
        balance_xpath = "//p[@id='wat-racer-mining--bht-text']"

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

    def get_profit_hour(self, claimed=False):

        self.driver.execute_script("location.href = 'https://prizes.gamee.com/telegram/mining/26'")

        prefix = "After" if claimed else "Before"
        default_priority = 2 if claimed else 3

        # Dynamically adjust the log priority
        priority = max(self.settings['verboseLevel'], default_priority)

        # Construct the specific profit XPath
        profit_text = f'{prefix} PROFIT/HOUR:'
        profit_xpath = "(//p[contains(@class, 'bXJWuE')])[1]"

        try:
            element = self.monitor_element(profit_xpath)
            if element:
                profit_part = self.strip_html_and_non_numeric(element)
                self.output(f"Step {self.step} - {profit_text} {profit_part}", priority)

        except NoSuchElementException:
            self.output(f"Step {self.step} - Element containing '{prefix} Profit/Hour:' was not found.", priority)
        except Exception as e:
            self.output(f"Step {self.step} - An error occurred: {str(e)}", priority)  # Provide error as string for logging

        # Increment step function, assumed to handle next step logic
        self.increase_step()

    def get_wait_time(self, step_number="108", beforeAfter="pre-claim"):
        try:
            self.output(f"Step {self.step} - Get the wait time...", 3)

            # XPath to find the element containing the wait time
            xpath = "//p[contains(text(), 'to claim')]"
            wait_time_text = self.monitor_element(xpath, 10, "claim timer")

            # Check if wait_time_text is not empty
            if wait_time_text:
                wait_time_text = wait_time_text.strip()
                self.output(f"Step {self.step} - Extracted wait time text: '{wait_time_text}'", 3)

                # Regular expression to find all numbers followed by 'h' or 'm', possibly with spaces
                pattern = r'(\d+)\s*([hH]|hours?|[mM]|minutes?)'
                matches = re.findall(pattern, wait_time_text)

                total_minutes = 0
                if matches:
                    for value, unit in matches:
                        unit = unit.lower()
                        if unit.startswith('h'):
                            total_minutes += int(value) * 60
                        elif unit.startswith('m'):
                            total_minutes += int(value)
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
    claimer = GameeClaimer()
    claimer.run()

if __name__ == "__main__":
    main()
