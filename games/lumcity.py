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

class LumCityClaimer(Claimer):

    def initialize_settings(self):
        super().initialize_settings()
        self.script = "games/lumcity.py"
        self.prefix = "LumCity:"
        self.url = "https://web.telegram.org/k/#@LumCity_bot"
        self.pot_full = "Filled"
        self.pot_filling = "to fill"
        self.seed_phrase = None
        self.forceLocalProxy = False
        self.forceRequestUserAgent = False
        self.allow_early_claim = False
        self.start_app_xpath = "//span[contains(text(), 'Open the App')]"

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
            self.set_cookies()
        except TimeoutException:
            self.output(f"Step {self.step} - Failed to find or switch to the iframe within the timeout period.", 1)
        except Exception as e:
            self.output(f"Step {self.step} - An error occurred: {e}", 1)

    def full_claim(self):
        self.step = "100"

        self.launch_iframe()
        self.output(f"Step {self.step} - Short wait to let the totals load", 3)
        time.sleep(10)

        try:
            golt_balance = float(self.get_balance(False))
        except (ValueError, TypeError):
            golt_balance = 0.0

        xpath = "//button[contains(normalize-space(.), 'Claim')]"
        self.move_and_click(xpath, 20, True, "move to the 'Claim' screen", self.step, "clickable")

        remaining_wait_time = self.get_wait_time(self.step, "pre-claim")
        self.get_profit_hour(False)

        try:
            remaining_wait_time = int(remaining_wait_time)
        except ValueError:
            self.output("STATUS: Wait time is unknown due to non-numeric input.", 1)
            return 60

        if remaining_wait_time > 0:
            if remaining_wait_time < 5 or self.settings["forceClaim"]:
                self.settings['forceClaim'] = True
                self.output(f"Step {self.step} - the remaining time to claim is less than the random offset, so applying: settings['forceClaim'] = True", 3)
            else:
                self.output(f"STATUS: Wait time is {remaining_wait_time} minutes and off-set of {self.random_offset}.", 1)
                return remaining_wait_time + self.random_offset

        try:
            if remaining_wait_time < 5 or self.settings['forceClaim']:
                
                self.handle_claim_process()

                claim_drop = False
                if self.attempt_upgrade(golt_balance):
                    claim_drop = True

                remaining_wait_time = self.get_wait_time(self.step, "post-claim")
                self.increase_step()

                xpath = "//button[contains(@class, 'backBtn')]"
                self.move_and_click(xpath, 20, True, "click the 'backBtn' button", self.step, "clickable")
                self.increase_step()
                
                self.output(f"Step {self.step} - Short wait to let the totals load", 3)
                time.sleep(10)
                
                try:
                    golt_balance = float(self.get_balance(True))
                except (ValueError, TypeError):
                    golt_balance = 0.0

                if claim_drop and golt_balance > 1:
                    self.output(f"Step {self.step} - Preparing to claim Drop", 3)
                    self.claim_drop(golt_balance) 
                elif claim_drop and not golt_balance > 1:
                    self.output(f"Step {self.step} - Insufficient Galt to claim Drop", 3)


                if remaining_wait_time == 0:
                    self.output(f"Step {self.step} - The wait timer is still showing: Filled.", 1)
                    self.output(f"Step {self.step} - This means either the claim failed, or there is lag in the game.", 1)
                    self.output(f"Step {self.step} - We'll check back in 1 hour to see if the claim processed and if not try again.", 2)
                    return 60
                else:
                    total_time = self.apply_random_offset(remaining_wait_time)
                    self.output(f"STATUS: Pot full in {remaining_wait_time} minutes, plus an off-set of {self.random_offset}.", 1)
                    return total_time

        except Exception as e:
            self.output(f"Step {self.step} - An unexpected error occurred: {e}", 1)
            return 60

    def attempt_upgrade(self):
        pass

    def handle_claim_process(self):
        try:
            xpath = "//button[contains(normalize-space(.), 'Claim')]"
            self.move_and_click(xpath, 20, True, "click the 'Claim' button", self.step, "clickable")
            self.increase_step()

            xpath = "//div[contains(@class, '_msgWrapper_7jeg3_57')]//span[1]"
            reward_value = self.monitor_element(xpath, 20, "balance increase value")
            if reward_value:
                self.output(f"Step {self.step} - This claim increased the balance: +{reward_value}", 1)

            xpath = "//div[contains(@class, '_btnContainer')]//button[text()='Ok']"
            self.move_and_click(xpath, 20, True, "click the 'OK' button", self.step, "clickable")
            self.increase_step()

            xpath = "//button[contains(@class, 'backBtn')]"
            self.move_and_click(xpath, 20, True, "click the 'backBtn' button", self.step, "clickable")
            self.increase_step()

            xpath = "//button[contains(normalize-space(.), 'Claim')]"
            self.move_and_click(xpath, 20, True, "move to the 'Claim' screen", self.step, "clickable")

        except Exception as e:
            self.output(f"Step {self.step} - An unexpected error occurred: {e}", 1)
            return 60
    def claim_drop(self):
        pass

    def get_balance(self, claimed=False):
        prefix = "After" if claimed else "Before"
        default_priority = 2 if claimed else 3

        priority = max(self.settings['verboseLevel'], default_priority)

        balance_text = f'{prefix} Golt BALANCE:' if claimed else f'{prefix} BALANCE:'
        balance_xpath = f"(//div[contains(@class, '1615f_24')])[2]"
        balance_part = None

        try:
            self.move_and_click(balance_xpath, 30, False, "look for Golt balance", self.step, "visible")
            balance_part = self.strip_html_tags(self.monitor_element(balance_xpath,15,"golt balance"))
            self.output(f"Step {self.step} - {balance_text} {balance_part}", priority)
            return balance_part
        except NoSuchElementException:
            self.output(f"Step {self.step} - Element containing '{prefix} Balance:' was not found.", priority)
        except Exception as e:
            self.output(f"Step {self.step} - An error occurred: {str(e)}", priority)

        self.increase_step()
        return balance_part  # Added return statement to ensure balance_part is returned

    def strip_html_tags(self, text):
        clean = re.compile('<.*?>')
        text_without_html = re.sub(clean, '', text)
        text_cleaned = re.sub(r'[^0-9:.]', '', text_without_html)
        return text_cleaned

    def extract_single_number(self, text):
        numbers = re.findall(r'[\d.]+', text)
        if numbers:
            return numbers[0]
        return None

    def extract_time(self, text):
        time_parts = text.split(':')
        if len(time_parts) == 3:
            try:
                hours = int(time_parts[0].strip())
                minutes = int(time_parts[1].strip())
                return hours * 60 + minutes
            except ValueError:
                return "Unknown"
        return "Unknown"

    def get_wait_time(self, step_number="108", beforeAfter="pre-claim", max_attempts=1):
        for attempt in range(1, max_attempts + 1):
            try:
                self.output(f"Step {self.step} - check if the timer is elapsing...", 3)
                xpath = "//span[text()='Fill Time']/ancestor::div[1]/following-sibling::div"
                pot_full_value = self.extract_time(self.strip_html_tags(self.monitor_element(xpath, 15, "wait time")))
                return pot_full_value
            except Exception as e:
                self.output(f"Step {self.step} - An error occurred on attempt {attempt}: {e}", 3)
                return "Unknown"
        return "Unknown"

    def send_start(self, old_step):
        xpath = "//div[contains(@class, 'input-message-container')]/div[contains(@class, 'input-message-input')][1]"
        
        def attempt_send_start():
            chat_input = self.move_and_click(xpath, 5, False, "find the chat window/message input box", self.step, "present")
            if chat_input:
                self.increase_step()
                self.output(f"Step {self.step} - Attempting to send the '/app' command...",2)
                chat_input.send_keys("/app")
                chat_input.send_keys(Keys.RETURN)
                self.output(f"Step {self.step} - Successfully sent the '/app' command.\n",3)
                if self.settings['debugIsOn']:
                    screenshot_path = f"{self.screenshots_path}/{self.step}-sent-start.png"
                    self.driver.save_screenshot(screenshot_path)
                return True
            else:
                self.output(f"Step {self.step} - Failed to find the message input box.\n",1)
                return False

        if not attempt_send_start():
            # Attempt failed, try restoring from backup and retry
            self.output(f"Step {self.step} - Attempting to restore from backup and retry.\n",2)
            if self.restore_from_backup(self.backup_path):
                if not attempt_send_start():  # Retry after restoring backup
                    self.output(f"Step {self.step} - Retried after restoring backup, but still failed to send the '/start' command.\n",1)
            else:
                self.output(f"Step {self.step} - Backup restoration failed or backup directory does not exist.\n",1)

    def get_profit_hour(self, claimed=False):
        prefix = "After" if claimed else "Before"
        default_priority = 2 if claimed else 3

        priority = max(self.settings['verboseLevel'], default_priority)

        # Construct the specific profit XPath
        profit_text = f'{prefix} PROFIT/HOUR:'
        profit_xpath = "//div[contains(@class, 'pickaxeUpgrade')]//div[last()]"

        try:
            element = self.strip_non_numeric(self.monitor_element(profit_xpath,15,"profit per hour"))
            # Check if element is not None and process the profit
            if element:
                self.output(f"Step {self.step} - {profit_text} {element}", priority)

        except NoSuchElementException:
            self.output(f"Step {self.step} - Element containing '{prefix} Profit/Hour:' was not found.", priority)
        except Exception as e:
            self.output(f"Step {self.step} - An error occurred: {str(e)}", priority)  # Provide error as string for logging
        
        self.increase_step()

def main():
    claimer = LumCityClaimer()
    claimer.run()

if __name__ == "__main__":
    main()