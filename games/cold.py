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

class ColdClaimer(Claimer):

    def initialize_settings(self):
        super().initialize_settings()
        self.script = "games/cold.py"
        self.prefix = "BNB-Cold:"
        self.url = "https://web.telegram.org/k/#@Newcoldwallet_bot"
        self.pot_full = "Filled"
        self.pot_filling = "Mining"
        self.seed_phrase = None
        self.forceLocalProxy = False
        self.forceRequestUserAgent = False
        self.start_app_xpath = "//button//span[contains(text(), 'Open Wallet')]"

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
            # Let's click the login button first:
            xpath = "//button[contains(text(), 'Log in')]"
            self.target_element = self.move_and_click(xpath, 20, False, "find log-in button (may not be present)", "08", "visible")
            self.driver.execute_script("arguments[0].click();", self.target_element)
            self.increase_step()

            self.set_cookies()

        except TimeoutException:
            self.output(f"Step {self.step} - Failed to find or switch to the iframe within the timeout period.",1)

        except Exception as e:
            self.output(f"Step {self.step} - An error occurred: {e}",1)

    def full_claim(self):
        self.step = "100"
        self.launch_iframe()

        # Click on the Storage link:
        xpath = "//h4[text()='Storage']"
        self.move_and_click(xpath, 30, True, "click the 'storage' link", self.step, "clickable")
        self.increase_step()

        self.get_balance(False)
        self.get_profit_hour(False)
        wait_time_text = self.get_wait_time(self.step, "pre-claim") 

        if wait_time_text != "Filled":
            self.output(f"STATUS: The pot is not yet full, we'll go back to sleep for 1 hour.", 1)
            return 60

        try:
            self.output(f"Step {self.step} - The pre-claim wait time is : {wait_time_text}", 1)
            self.increase_step()

            if wait_time_text == "Filled" or self.settings['forceClaim']:
                try:
                    original_window = self.driver.current_window_handle
                    xpath = "//button[contains(text(), 'Check News')]"
                    button = self.move_and_click(xpath, 10, True, "check for NEWS (may not be present).", self.step, "clickable")
                    if button:
                        self.output(f"Step {self.step} - Clicked the Check News button...", 2)
                    self.driver.switch_to.window(original_window)
                    self.increase_step()
                    self.select_iframe(self.step)
                    self.increase_step()
                except TimeoutException:
                    if self.settings['debugIsOn']:
                        self.output(f"Step {self.step} - No news to check or button not found.", 3)

                # Single attempt to click the Claim buttons
                try:
                    # Click on the "Claim" button:
                    xpath = "//button[contains(text(), 'Claim')]"
                    self.move_and_click(xpath, 10, True, "click the 1st claim button", self.step, "clickable")
                    self.increase_step()

                    xpath = '//div[contains(@class, "react-responsive-modal-modal")]//button[contains(@class, "btn-primary") and text()="Claim"]'
                    self.move_and_click(xpath, 10, True, "click the 2nd claim button", self.step, "clickable")
                    self.output(f"Step {self.step} - Clicked the 2nd claim button...", 2)
                    self.increase_step()

                    # Wait for the spinner to disappear before trying to get the new time to fill.
                    self.output(f"Step {self.step} - Let's wait for the pending Claim spinner to stop spinning...", 2)
                    time.sleep(20)

                    self.get_balance(True)
                    self.get_profit_hour(True)
                    wait_time_text = self.get_wait_time(self.step, "post-claim")

                    if wait_time_text != "Filled":
                        self.output(f"STATUS: Successful Claim: We'll check back hourly for the pot to be full.", 1)
                        return 60
                    else:
                        self.output(f"STATUS: The wait timer is still showing: Filled.", 1)
                        self.output(f"Step {self.step} - This means either the claim failed, or there is lag in the game.", 1)

                except TimeoutException:
                    self.output(f"STATUS: The claim process timed out: Maybe the site has lag? Will retry after one hour.", 1)
                    return 60
                except Exception as e:
                    self.output(f"STATUS: An error occurred while trying to claim: {e}", 1)
                    return 60

            # Check if the status is still "Filled" outside the try block
            self.get_balance(True)
            self.get_profit_hour(True)
            wait_time_text = self.get_wait_time(self.step, "post-claim")
            if wait_time_text != "Filled":
                self.output(f"STATUS: Successful Claim: We'll check back hourly for the pot to be full.", 1)
                return 60

            self.output(f"Step {self.step} - Exhausted all claim attempts. We'll check back in 1 hour to see if the claim processed and if not try again.", 2)
            return 60

        except TimeoutException:
            self.output(f"STATUS: The claim process timed out: Maybe the site has lag? Will retry after one hour.", 1)
            return 60
        except Exception as e:
            self.output(f"STATUS: An error occurred while trying to claim: {e}\nLet's wait an hour and try again", 1)
            return 60

    def get_balance(self, claimed=False):

        prefix = "After" if claimed else "Before"
        default_priority = 2 if claimed else 3

        # Dynamically adjust the log priority
        priority = max(self.settings['verboseLevel'], default_priority)

        # Construct the specific balance XPath
        balance_text = f'{prefix} BALANCE:'
        balance_xpath = f"(//img[@alt='COLD']/following-sibling::p)[last()]"

        try:
            element = self.monitor_element(balance_xpath)

            # Check if element is not None and process the balance
            if element:
                cleaned_balance = self.strip_html_and_non_numeric(element)
                self.output(f"Step {self.step} - {balance_text} {cleaned_balance}", priority)

        except NoSuchElementException:
            self.output(f"Step {self.step} - Element containing '{prefix} Balance:' was not found.", priority)
        except Exception as e:
            self.output(f"Step {self.step} - An error occurred: {str(e)}", priority)  # Provide error as string for logging

        # Increment step function, assumed to handle next step logic
        self.increase_step()

    def get_profit_hour(self, claimed=False):

        prefix = "After" if claimed else "Before"
        default_priority = 2 if claimed else 3

        # Dynamically adjust the log priority
        priority = max(self.settings['verboseLevel'], default_priority)

        # Construct the specific profit XPath
        profit_text = f'{prefix} PROFIT/HOUR:'
        profit_xpath = "//div[p[text()='Frost Box']]//p[last()]"

        try:
            element = self.strip_non_numeric(self.monitor_element(profit_xpath))

            # Check if element is not None and process the profit
            if element:
                self.output(f"Step {self.step} - {profit_text} {element}", priority)

        except NoSuchElementException:
            self.output(f"Step {self.step} - Element containing '{prefix} Profit/Hour:' was not found.", priority)
        except Exception as e:
            self.output(f"Step {self.step} - An error occurred: {str(e)}", priority)  # Provide error as string for logging

        # Increment step function, assumed to handle next step logic
        self.increase_step()


    def get_wait_time(self, step_number="108", beforeAfter="pre-claim"):
        try:
            xpath = "//p[contains(text(), 'Filled')]"
            wait_time_element = self.move_and_click(xpath, 10, False, f"get the {beforeAfter} wait timer", step_number, "visible")

            # Check if wait_time_element is not None
            if wait_time_element is not None:
                return "Filled"
            else:
                return "Mining"
        except Exception as e:
            self.output(f"Step {self.step} - An error occurred: {e}", 3)
            if self.settings['debugIsOn']:
                screenshot_path = f"{self.screenshots_path}/{self.step}_get_wait_time_error.png"
                self.driver.save_screenshot(screenshot_path)
                self.output(f"Screenshot saved to {screenshot_path}", 3)
            return False

def main():
    claimer = ColdClaimer()
    claimer.run()

if __name__ == "__main__":
    main()