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

class DiamondClaimer(Claimer):

    def initialize_settings(self):
        super().initialize_settings()
        self.script = "games/diamond.py"
        self.prefix = "Diamond:"
        self.url = "https://web.telegram.org/k/#@holdwallet_bot"
        self.pot_full = "Filled"
        self.pot_filling = "to fill"
        self.seed_phrase = None
        self.forceLocalProxy = False
        self.forceRequestUserAgent = False
        self.start_app_xpath = "//div[text()='Open Wallet']"

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
            xpath = "//a[contains(text(), 'Login')]"
            self.target_element = self.move_and_click(xpath, 30, False, "find the HoldWallet log-in button", "08", "visible")
            self.driver.execute_script("arguments[0].click();", self.target_element)
            self.increase_step()

            # Then look for the seed phase textarea:
            xpath = "//div[@class='form-input'][label[text()='Seed or private key']]/textarea"
            input_field = self.move_and_click(xpath, 30, True, "locate seedphrase textbox", self.step, "clickable")
            if not self.imported_seedphrase:
                self.imported_seedphrase = self.validate_seed_phrase()
            input_field.send_keys(self.imported_seedphrase) 
            self.output(f"Step {self.step} - Was successfully able to enter the seed phrase...",3)
            self.increase_step()

            # Click the continue button after seed phrase entry:
            xpath = "//button[contains(text(), 'Continue')]"
            self.move_and_click(xpath, 30, True, "click continue after seedphrase entry", self.step, "clickable")
            self.increase_step()

            # Click the account selection button:
            xpath = "//div[contains(text(), 'Select account')]"
            self.move_and_click(xpath, 20, True, "click account selection (may not be present)", self.step, "clickable")
            self.increase_step()

            if not (self.forceRequestUserAgent or self.settings["requestUserAgent"]):
                cookies_path = f"{self.session_path}/cookies.json"
                cookies = self.driver.get_cookies()
                with open(cookies_path, 'w') as file:
                    json.dump(cookies, file)
            else:
                user_agent = self.prompt_user_agent()
                cookies_path = f"{self.session_path}/cookies.json"
                cookies = self.driver.get_cookies()
                cookies.append({"name": "user_agent", "value": user_agent})  # Save user agent to cookies
                with open(cookies_path, 'w') as file:
                    json.dump(cookies, file)

        except TimeoutException:
            self.output(f"Step {self.step} - Failed to find or switch to the iframe within the timeout period.",1)

        except Exception as e:
            self.output(f"Step {self.step} - An error occurred: {e}",1)

    def full_claim(self):
        self.step = "100"

        self.launch_iframe()

        # Best on Standalone:
        xpath = "//p[text()='Storage']"
        self.move_and_click(xpath, 15, True, "click the 'storage' link", self.step, "clickable")
        self.increase_step

        # Best on Docker!:
        xpath = "//h2[text()='Mining']"
        self.move_and_click(xpath, 15, True, "click the alternative 'storage' link (may not be present)", self.step, "clickable")
        self.increase_step

        self.get_balance(False)
        self.get_profit_hour(False)

        wait_time_text = self.get_wait_time(self.step, "pre-claim") 

        if wait_time_text != "0h 0m to fill":
            matches = re.findall(r'(\d+)([hm])', wait_time_text)
            remaining_wait_time = (sum(int(value) * (60 if unit == 'h' else 1) for value, unit in matches)) + self.random_offset
            if remaining_wait_time < 5 or self.settings["forceClaim"]:
                self.settings['forceClaim'] = True
                self.output(f"Step {self.step} - the remaining time to claim is less than the random offset, so applying: settings['forceClaim'] = True", 3)
            else:
                self.output(f"STATUS: Considering {wait_time_text}, we'll go back to sleep for {remaining_wait_time} minutes.", 1)
                return remaining_wait_time

        if wait_time_text == "Unknown":
            return 15

        try:
            self.output(f"Step {self.step} - The pre-claim wait time is : {wait_time_text} and random offset is {self.random_offset} minutes.",1)
            self.increase_step()

            if wait_time_text == "0h 0m to fill" or self.settings['forceClaim']:
                try:

                    # Let's see if we have news to read
                    try:
                        original_window = self.driver.current_window_handle
                        xpath = "//button[contains(text(), 'Check NEWS')]"
                        success = self.move_and_click(xpath, 10, True, "check for NEWS.", self.step, "clickable")
                        if success:
                            self.output(f"Step {self.step} - atempting to switch back to iFrame.")
                            self.driver.switch_to.window(original_window)
                    except TimeoutException:
                        if self.settings['debugIsOn']:
                            self.output(f"Step {self.step} - No news to check or button not found.", 3)
                    self.increase_step()


                    # Click on the "Claim" button:
                    xpath = "//button[contains(text(), 'Claim')]"
                    self.move_and_click(xpath, 30, True, "click the claim button", self.step, "clickable")
                    self.increase_step()

                    # Now let's try again to get the time remaining until filled. 
                    # 4th April 24 - Let's wait for the spinner to disappear before trying to get the new time to fill.
                    self.output(f"Step {self.step} - Let's wait for the pending Claim spinner to stop spinning...",2)
                    time.sleep(5)
                    wait_time_text = self.get_wait_time(self.step, "post-claim") 
                    matches = re.findall(r'(\d+)([hm])', wait_time_text)
                    total_wait_time = self.apply_random_offset(sum(int(value) * (60 if unit == 'h' else 1) for value, unit in matches))
                    self.increase_step()

                    self.get_balance(True)
                    self.get_profit_hour(True)

                    if wait_time_text == "0h 0m to fill":
                        self.output(f"STATUS: The wait timer is still showing: Filled.",1)
                        self.output(f"Step {self.step} - This means either the claim failed, or there is >4 minutes lag in the game.",1)
                        self.output(f"Step {self.step} - We'll check back in 1 hour to see if the claim processed and if not try again.",2)
                    else:
                        self.output(f"STATUS: Successful Claim: Next claim {wait_time_text} / {total_wait_time} minutes.",1)
                    return max(60, total_wait_time)

                except TimeoutException:
                    self.output(f"STATUS: The claim process timed out: Maybe the site has lag? Will retry after one hour.",1)
                    return 60
                except Exception as e:
                    self.output(f"STATUS: An error occurred while trying to claim: {e}\nLet's wait an hour and try again",1)
                    return 60

            else:
                # If the wallet isn't ready to be claimed, calculate wait time based on the timer provided on the page
                matches = re.findall(r'(\d+)([hm])', wait_time_text)
                if matches:
                    total_time = sum(int(value) * (60 if unit == 'h' else 1) for value, unit in matches)
                    total_time += 1
                    total_time = max(5, total_time) # Wait at least 5 minutes or the time
                    self.output(f"Step {self.step} - Not Time to claim this wallet yet. Wait for {total_time} minutes until the storage is filled.",2)
                    return total_time 
                else:
                    self.output(f"Step {self.step} - No wait time data found? Let's check again in one hour.",2)
                    return 60  # Default wait time when no specific time until filled is found.
        except Exception as e:
            self.output(f"Step {self.step} - An unexpected error occurred: {e}",1)
            return 60  # Default wait time in case of an unexpected error
        
    def get_balance(self, claimed=False):

        prefix = "After" if claimed else "Before"
        default_priority = 2 if claimed else 3

        # Dynamically adjust the log priority
        priority = max(self.settings['verboseLevel'], default_priority)

        # Construct the specific balance XPath
        balance_text = f'{prefix} BALANCE:' if claimed else f'{prefix} BALANCE:'
        balance_xpath = f"//small[text()='DMH Balance']/following-sibling::div"

        try:
            element = self.strip_html_and_non_numeric(self.monitor_element(balance_xpath))

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

        # Dynamically adjust the log priority
        priority = max(self.settings['verboseLevel'], default_priority)

        # Construct the specific profit XPath
        profit_text = f'{prefix} PROFIT/HOUR:'
        profit_xpath = "//div[div[p[text()='Storage']]]//span[last()]"

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
            xpath = "//div[div[p[text()='Storage']]]//span[contains(text(), 'to fill') or contains(text(), 'Filled')]"
            wait_time_element = self.move_and_click(xpath, 20, True, f"get the {beforeAfter} wait timer", step_number, "visible")
            # Check if wait_time_element is not None
            if wait_time_element is not None:
                return wait_time_element.text
            else:
                return "Unknown"
        except Exception as e:
            self.output(f"Step {step_number} - An error occurred: {e}", 3)
            return "Unknown"

def main():
    claimer = DiamondClaimer()
    claimer.run()

if __name__ == "__main__":
    main()