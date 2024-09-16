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

class SeedClaimer(Claimer):

    def initialize_settings(self):
        super().initialize_settings()
        self.script = "games/seed.py"
        self.prefix = "Seed:"
        self.url = "https://web.telegram.org/k/#@seed_coin_bot"
        self.pot_full = "Filled"
        self.pot_filling = "to fill"
        self.seed_phrase = None
        self.forceLocalProxy = False
        self.forceRequestUserAgent = False
        self.allow_early_claim = False
        self.start_app_xpath = "//button[descendant::span[contains(text(), 'Play')]]"

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

            cookies_path = f"{self.session_path}/cookies.json"
            cookies = self.driver.get_cookies()
            with open(cookies_path, 'w') as file:
                json.dump(cookies, file)

        except TimeoutException:
            self.output(f"Step {self.step} - Failed to find or switch to the iframe within the timeout period.",1)

        except Exception as e:
            self.output(f"Step {self.step} - An error occurred: {e}",1)

    def get_daily_bonus(self):

        xpath = "//img[@alt='Earn']"
        self.move_and_click(xpath, 10, True, "click the 'Missions' tab", self.step, "clickable")

        xpath = "//p[contains(text(), 'Login Bonus')]/following::button[1]"
        self.move_and_click(xpath, 10, True, "click the 'Login Bonus' tab (may not be present)", self.step, "clickable")
        
        xpath = "//button[not(contains(@class, 'pointer-events-none')) and .//img[contains(@src, '/images/daily')]]"
        success = self.move_and_click(xpath, 10, True, "click the active reward image", self.step, "clickable")
        if not success:
            self.output(f"Step {self.step} - Looks like the daily reward has already been claimed.",3)
            return

        self.output(f"STATUS: Daily reward claimed.",1)

        xpath = "//button[contains(text(), 'Got it')]"
        self.move_and_click(xpath, 10, True, "click the 'Got it' button (may not be present)", self.step, "clickable")

        xpath = "//button[contains(text(), 'Claim 1 ticket')]"
        self.move_and_click(xpath, 10, True, "get Ticket (may not be present)", self.step, "clickable")

    def full_claim(self):
        self.step = "100"

        self.launch_iframe()
        self.increase_step()

        xpath = "//p[contains(text(), 'Claim')]"
        self.move_and_click(xpath, 10, True, "check for Mystery Box (may not be present)", self.step, "clickable")
        self.increase_step()

        xpath = "//div[contains(text(), 'Tap 10')]"    
        self.move_and_click(xpath, 10, True, "check if tree tap blocking game (may not be present)", self.step, "clickable")
        self.increase_step()

        self.get_balance(False)

        xpath = "//button[contains(text(), 'CHECK NEWS')]"
        self.move_and_click(xpath, 10, True, "check for NEWS (may not be present)", self.step, "clickable")
        self.increase_step()

        # GET WORM
        xpath = "//img[contains(@src,'inventory/worm')]"
        self.move_and_click(xpath, 10, True, "check for WORM (may not be present)", self.step, "clickable")
        self.increase_step()

        xpath = "//button[.//p[contains(text(), 'Yep')]]"
        self.move_and_click(xpath, 10, True, "click Yep button WORM (may not be present)", self.step, "clickable")
        self.increase_step()

        # Get egg
        xpath = "//img[contains(@src, 'bird.png')]"
        self.move_and_click(xpath, 10, True, "check for EGG (may not be present)", self.step, "clickable")
        self.increase_step()

        remaining_wait_time = self.get_wait_time(self.step, "pre-claim") 
        if not remaining_wait_time or self.settings["forceClaim"]:
            self.output(f"Step {self.step} - looks like we're ready to claim.", 3)
        else:
            remaining_time = self.apply_random_offset(remaining_wait_time)
            self.output(f"STATUS: Original wait time {remaining_wait_time} minutes, We'll sleep for {remaining_time} minutes after random offset.", 1)
            return remaining_time

        try:
            xpath = "//div[contains(@class, 'rounded') and descendant::p[contains(text(), 'Claim')]]"
            button = self.move_and_click(xpath, 10, True, "click the 'Claim' button", self.step, "clickable")
            self.increase_step()

            # Wait for the totals and timer to update.
            self.output(f"Step {self.step} - Waiting 5 seconds for the totals and timer to update...", 3)
            time.sleep(5)

            xpath = "//button[.//p[contains(text(), 'Yep')]]"
            self.move_and_click(xpath, 10, True, "click Yep button WORM (may not be present)", self.step, "clickable")
            self.increase_step()

            remaining_wait_time = self.get_wait_time(self.step, "post-claim")
            self.get_balance(True)
            self.get_daily_bonus()

            if not remaining_wait_time:
                self.output(f"STATUS: The wait timer is still showing: Filled.", 1)
                self.output(f"Step {self.step} - This means either the claim failed, or there is lag in the game.", 1)
                self.output(f"Step {self.step} - We'll check back in 1 hour to see if the claim processed and if not try again.", 2)
                return 60

            remaining_time = self.apply_random_offset(remaining_wait_time)
            self.output(f"STATUS: Original wait time {remaining_wait_time} minutes, We'll sleep for {remaining_time} minutes after random offset.", 1)
            return remaining_time

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
        balance_xpath = "//img[@alt='token']/ancestor::div[1]/following-sibling::p[contains(@class, 'text-[32px]')]"

        try:
            element = self.monitor_element(balance_xpath, 15, "get balance")
            if element:
                # If element exists, send it as it is
                self.output(f"Step {self.step} - {prefix} BALANCE: {element}", priority)

        except NoSuchElementException:
            self.output(f"Step {self.step} - Element containing '{prefix} Balance:' was not found.", priority)
        except Exception as e:
            self.output(f"Step {self.step} - An error occurred: {str(e)}", priority)  # Provide error as string for logging

        # Increment step function, assumed to handle next step logic
        self.increase_step()

    def get_profit_hour(self, claimed=False):
        # currently broken!
        return

        prefix = "After" if claimed else "Before"
        default_priority = 2 if claimed else 3

        # Dynamically adjust the log priority
        priority = max(self.settings['verboseLevel'], default_priority)

        # Construct the specific profit XPath
        profit_text = f'{prefix} PROFIT/HOUR:'
        profit_xpath = "//p[contains(text(), 'SEED/hour')]"

        try:
            element = self.monitor_element(profit_xpath, 15, "profit per hour")
            if isinstance(element, str):
                # Split element at the colon (if present) and assign the right side (excluding ":")
                if ' ' in element:
                    element = element.split(' ')[0].strip()
            # Check if element is not None and process the balance
            if element:
                profit_part = element
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
            xpath = "//div[@class='grid grid-cols-[repeat(7,auto)]']"
            elements = self.monitor_element(xpath, 10, "claim timer")
            
            # If elements are found, extract their text content
            if elements:
                wait_time_text = elements
                
                # Clean up the text by removing spaces before "h" and "m"
                wait_time_text = wait_time_text.replace(" h ", "h ").replace(" m ", "m ").replace(" ", "")
                
                # Initialize minutes to 0
                total_minutes = 0
                
                # Extract hours and minutes
                if 'h' in wait_time_text:
                    # Split by 'h' to get hours and the rest of the string
                    parts = wait_time_text.split('h')
                    # Convert hours to minutes
                    hours_in_minutes = int(parts[0]) * 60
                    total_minutes += hours_in_minutes
                    # Check if there are minutes after 'h'
                    if 'm' in parts[1]:
                        minutes = int(parts[1].replace('m', ''))
                        total_minutes += minutes
                elif 'm' in wait_time_text:
                    # If there are only minutes
                    total_minutes += int(wait_time_text.replace('m', ''))
                
                # Return total minutes if greater than zero, else False
                return total_minutes if total_minutes > 0 else False
            
            return False
        except Exception as e:
            self.output(f"Step {self.step} - An error occurred: {e}", 3)
            return False

def main():
    claimer = SeedClaimer()
    claimer.run()

if __name__ == "__main__":
    main()
