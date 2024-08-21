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

class WaveClaimer(Claimer):

    def initialize_settings(self):
        super().initialize_settings()
        self.script = "games/wave.py"
        self.prefix = "Wave:"
        self.url = "https://web.telegram.org/k/#@waveonsuibot"
        self.pot_full = "Filled"
        self.pot_filling = "to fill"
        self.seed_phrase = None
        self.forceLocalProxy = False
        self.forceRequestUserAgent = False
        self.start_app_xpath = "//a[@href='https://t.me/waveonsuibot/walletapp']"

    def __init__(self):
        self.settings_file = "variables.txt"
        self.status_file_path = "status.txt"
        self.wallet_id = ""
        self.load_settings()
        self.random_offset = random.randint(self.settings['lowestClaimOffset'], self.settings['highestClaimOffset']) + 1
        super().__init__()

    def next_steps(self):
        if self.step:
            pass
        else:
            self.step = "01"

        try:
            self.launch_iframe()
            self.increase_step()

            try:
                xpath = "//button[contains(text(), 'Login')]"
                login_button = WebDriverWait(self.driver, 30).until(
                    EC.visibility_of_element_located((By.XPATH, xpath))
                )
        
                self.driver.execute_script("arguments[0].click();", login_button)
                self.output(f"Step {self.step} - Was successfully able to click on the login button...", 2)
                self.increase_step()

            except Exception as e:
                self.output(f"Step {self.step} - Failed to enter the seed phrase: {str(e)}", 2)

            try:
                xpath = "//p[contains(text(), 'Seed phrase or Private key')]/following-sibling::textarea[1]"
                input_field = WebDriverWait(self.driver, 30).until(
                    EC.visibility_of_element_located((By.XPATH, xpath))
                )
        
                self.driver.execute_script("arguments[0].click();", input_field)
                input_field.send_keys(self.validate_seed_phrase())
                self.output(f"Step {self.step} - Was successfully able to enter the seed phrase...", 3)
                self.increase_step()

            except Exception as e:
                self.output(f"Step {self.step} - Failed to enter the seed phrase: {str(e)}", 2)

            xpath = "//button[contains(text(), 'Continue')]"
            self.move_and_click(xpath, 30, True, "click continue after seedphrase entry", self.step, "clickable")
            self.increase_step()

            xpath = "//button[.//span[contains(text(), 'Claim Now')]]"
            self.move_and_click(xpath, 30, True, "click the 'Claim Now' link", self.step, "clickable")

            self.set_cookies()

        except TimeoutException:
            self.output(f"Step {self.step} - Failed to find or switch to the iframe within the timeout period.", 1)

        except Exception as e:
            self.output(f"Step {self.step} - An error occurred: {e}", 1)

    def full_claim(self):
        self.step = "100"

        def apply_random_offset(unmodifiedTimer):
            lowest_claim_offset = max(0, self.settings['lowestClaimOffset'])
            highest_claim_offset = max(0, self.settings['highestClaimOffset'])
            if self.settings['lowestClaimOffset'] <= self.settings['highestClaimOffset']:
                self.random_offset = random.randint(lowest_claim_offset, highest_claim_offset) + 1
                modifiedTimer = unmodifiedTimer + self.random_offset
                self.output(f"Step {self.step} - Random offset applied to the wait timer of: {self.random_offset} minutes.", 2)
                return modifiedTimer

        self.launch_iframe()

        xpath = "//button//span[contains(text(), 'Claim Now')]"
        button = self.move_and_click(xpath, 10, False, "click the 'Ocean Game' link", self.step, "visible")
        self.driver.execute_script("arguments[0].click();", button)
        self.increase_step()

        self.get_balance(False)
        self.get_profit_hour(False)

        wait_time_text = self.get_wait_time(self.step, "pre-claim")

        if wait_time_text != self.pot_full:
            matches = re.findall(r'(\d+)([hm])', wait_time_text)
            remaining_wait_time = (sum(int(value) * (60 if unit == 'h' else 1) for value, unit in matches))
            if remaining_wait_time < 5 or self.settings["forceClaim"]:
                self.settings['forceClaim'] = True
                self.output(f"Step {self.step} - the remaining time to claim is short so let's claim anyway, so applying: settings['forceClaim'] = True", 3)
            else:
                remaining_wait_time += self.random_offset
                self.output(f"STATUS: Considering {wait_time_text}, we'll go back to sleep for {remaining_wait_time} minutes.", 1)
                return remaining_wait_time

        if not wait_time_text:
            return 60

        try:
            self.output(f"Step {self.step} - The pre-claim wait time is : {wait_time_text} and random offset is {self.random_offset} minutes.", 1)
            self.increase_step()

            if wait_time_text == self.pot_full or self.settings['forceClaim']:
                try:
                    xpath = "//div[contains(text(), 'Claim Now')]"
                    button = self.move_and_click(xpath, 10, False, "click the claim button", self.step, "present")
                    try:
                        self.driver.execute_script("arguments[0].click();", button)
                        self.increase_step()
                    except Exception:
                        pass

                    self.output(f"Step {self.step} - Let's wait for the pending Claim spinner to stop spinning...", 2)
                    time.sleep(5)
                    wait = WebDriverWait(self.driver, 240)
                    spinner_xpath = "//*[contains(@class, 'spinner')]"
                    try:
                        wait.until(EC.invisibility_of_element_located((By.XPATH, spinner_xpath)))
                        self.output(f"Step {self.step} - Pending action spinner has stopped.\n", 3)
                    except TimeoutException:
                        self.output(f"Step {self.step} - Looks like the site has lag - the Spinner did not disappear in time.\n", 2)
                    self.increase_step()
                    wait_time_text = self.get_wait_time(self.step, "post-claim")
                    matches = re.findall(r'(\d+)([hm])', wait_time_text)
                    total_wait_time = apply_random_offset(sum(int(value) * (60 if unit == 'h' else 1) for value, unit in matches))
                    self.increase_step()

                    self.get_balance(True)

                    if wait_time_text == self.pot_full:
                        self.output(f"STATUS: The wait timer is still showing: Filled.", 1)
                        self.output(f"Step {self.step} - This means either the claim failed, or there is >4 minutes lag in the game.", 1)
                        self.output(f"Step {self.step} - We'll check back in 1 hour to see if the claim processed and if not try again.", 2)
                    else:
                        self.output(f"STATUS: Successful Claim: Next claim {wait_time_text} / {total_wait_time} minutes.", 1)
                    return max(60, total_wait_time)

                except TimeoutException:
                    self.output(f"STATUS: The claim process timed out: Maybe the site has lag? Will retry after one hour.", 1)
                    return 60
                except Exception as e:
                    self.output(f"STATUS: An error occurred while trying to claim: {e}\nLet's wait an hour and try again", 1)
                    return 60

            else:
                matches = re.findall(r'(\d+)([hm])', wait_time_text)
                if matches:
                    total_time = sum(int(value) * (60 if unit == 'h' else 1) for value, unit in matches)
                    total_time += 1
                    total_time = max(5, total_time)
                    self.output(f"Step {self.step} - Not Time to claim this wallet yet. Wait for {total_time} minutes until the storage is filled.", 2)
                    return total_time
                else:
                    self.output(f"Step {self.step} - No wait time data found? Let's check again in one hour.", 2)
                    return 60
        except Exception as e:
            self.output(f"Step {self.step} - An unexpected error occurred: {e}", 1)
            return 60
        
    def get_balance(self, claimed=False):
        prefix = "After" if claimed else "Before"
        default_priority = 2 if claimed else 3

        priority = max(self.settings['verboseLevel'], default_priority)

        balance_text = f'{prefix} BALANCE:' if claimed else f'{prefix} BALANCE:'
        xpath = "//p[contains(@class, 'wave-balance')]"

        try:
            element = WebDriverWait(self.driver, 20).until(
                EC.presence_of_element_located((By.XPATH, xpath))
            )

            balance_part = self.driver.execute_script("return arguments[0].textContent.trim();", element)
            
            if balance_part:
                self.output(f"Step {self.step} - {balance_text} {balance_part}", priority)
                return balance_part

        except NoSuchElementException:
            self.output(f"Step {self.step} - Element containing '{prefix} Balance:' was not found.", priority)
        except Exception as e:
            self.output(f"Step {self.step} - An error occurred: {str(e)}", priority)

        self.increase_step()

    def get_wait_time(self, step_number="108", beforeAfter="pre-claim", max_attempts=2):
        for attempt in range(1, max_attempts + 1):
            try:
                xpath = "//span[contains(@class, 'boat_balance')]"
                wait_time_element = self.move_and_click(xpath, 5, True, f"get the {beforeAfter} wait timer (time elapsing method)", self.step, "present")
                if wait_time_element is not None:
                    return wait_time_element.text
                xpath = "//div[contains(text(), 'Claim Now')]"
                wait_time_element = self.move_and_click(xpath, 10, False, f"get the {beforeAfter} wait timer (pot full method)", self.step, "present")
                if wait_time_element is not None:
                    return self.pot_full
                    
            except Exception as e:
                self.output(f"Step {self.step} - An error occurred on attempt {attempt}: {e}", 3)

        return False

    def get_profit_hour(self, claimed=False):
        prefix = "After" if claimed else "Before"
        default_priority = 2 if claimed else 3

        priority = max(self.settings['verboseLevel'], default_priority)

        # Construct the specific profit XPath
        profit_text = f'{prefix} PROFIT/HOUR:'
        profit_xpath = "//span[text()='Aqua Cat']/following-sibling::span[1]"

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
    claimer = WaveClaimer()
    claimer.run()

if __name__ == "__main__":
    main()