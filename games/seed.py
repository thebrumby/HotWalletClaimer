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
        self.start_app_xpath = "//div[text()='Play']"

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

        xpath = "//img[@alt='Missions']"
        self.move_and_click(xpath, 10, True, "click the 'Missions' tab", self.step, "clickable")

        xpath = "//p[text()='Login Bonus']"
        self.move_and_click(xpath, 10, True, "click the 'Login Bonus' tab (may not be present)", self.step, "clickable")
        
        xpath = "//button[not(contains(@class, 'pointer-events-none')) and .//img[contains(@src, '/images/daily')]]"
        self.move_and_click(xpath, 10, True, "click the active reward image", self.step, "clickable")

        xpath = "//button[contains(text(), 'Got it')]"
        self.move_and_click(xpath, 10, True, "click the 'Got it' button (may not be present)", self.step, "clickable")

        xpath = "//button[contains(text(), 'Claim 1 ticket')]"
        self.move_and_click(xpath, 10, True, "get Ticket (may not be present)", self.step, "clickable")

    def full_claim(self):
        self.step = "100"
            
        self.launch_iframe()

        xpath = "//button[contains(text(), 'Claim')]"
        self.move_and_click(xpath, 10, True, "check for Mystery Box (may not be present)", self.step, "clickable")

        xpath = "//div[contains(text(), 'Tap 10')]"    
        self.move_and_click(xpath, 10, True, "check if tree tap blocking game (may not be present)", self.step, "clickable")
        self.increase_step()

        self.get_balance(False)
        
        xpath = "//button[contains(text(), 'CHECK NEWS')]"
        self.move_and_click(xpath, 10, True, "check for NEWS (may not be present)", self.step, "clickable")

        self.get_profit_hour(False)
        
        # GET WORM
        xpath = "//img[contains(@src,'inventory/worm')]"
        self.move_and_click(xpath, 10, True, "check for WORM (may not be present)", self.step, "clickable")

        xpath = "//button[.//p[contains(text(), 'Yep')]]"
        self.move_and_click(xpath, 10, True, "click Yep button WORM (may not be present)", self.step, "clickable")

        # Get egg
        xpath = "//img[contains(@src, 'bird.png')]"
        self.move_and_click(xpath, 10, True, "check for EGG (may not be present)", self.step, "clickable")
        
        wait_time_text = self.get_wait_time(self.step, "pre-claim") 

        if wait_time_text != "Filled":
            matches = re.findall(r'(\d+)([hm])', wait_time_text)
            remaining_wait_time = (sum(int(value) * (60 if unit == 'h' else 1) for value, unit in matches)) + self.random_offset
            if remaining_wait_time < 5 or self.settings["forceClaim"]:
                self.settings['forceClaim'] = True
                self.output(f"Step {self.step} - the remaining time to claim is less than the random offset, so applying: settings['forceClaim'] = True", 3)
            else:
                self.output(f"STATUS: Considering {wait_time_text}, we'll go back to sleep for {remaining_wait_time} minutes.", 1)
                return remaining_wait_time

        if not wait_time_text:
            return 60

        try:
            self.output(f"Step {self.step} - The pre-claim wait time is : {wait_time_text} and random offset is {self.random_offset} minutes.", 1)
            self.increase_step()

            if wait_time_text == "Filled" or self.settings['forceClaim']:
                try:
                    xpath = "//button[contains(text(), 'Claim')]"
                    button = self.move_and_click(xpath, 10, True, "click the 'Claim' button", self.step, "clickable")
                    self.increase_step()

                    # Now let's give the site a few seconds to update.
                    self.output(f"Step {self.step} - Waiting 10 seconds for the totals and timer to update...", 3)
                    time.sleep(10)

                    xpath = "//button[.//p[contains(text(), 'Yep')]]"
                    self.move_and_click(xpath, 10, True, "click Yep button WORM (may not be present)", self.step, "clickable")

                    wait_time_text = self.get_wait_time(self.step, "post-claim")
                    matches = re.findall(r'(\d+)([hm])', wait_time_text)
                    total_wait_time = self.apply_random_offset(sum(int(value) * (60 if unit == 'h' else 1) for value, unit in matches))
                    self.increase_step()

                    self.get_balance(True)
                    self.get_profit_hour(True)
                    self.get_daily_bonus()

                    if wait_time_text == "Filled":
                        self.output(f"STATUS: The wait timer is still showing: Filled.", 1)
                        self.output(f"Step {self.step} - This means either the claim failed, or there is >4 minutes lag in the game.", 1)
                        self.output(f"Step {self.step} - We'll check back in 1 hour to see if the claim processed and if not try again.", 2)
                    else:
                        self.output(f"STATUS: Successful Claim: Next claim {wait_time_text} / {total_wait_time} minutes.",1)
                    return max(60, total_wait_time)

                except TimeoutException:
                    self.output(f"STATUS: The claim process timed out: Maybe the site has lag? Will retry after one hour.", 1)
                    return 60
                except Exception as e:
                    self.output(f"STATUS: An error occurred while trying to claim: {e}\nLet's wait an hour and try again", 1)
                    return 60

            else:
                # If the wallet isn't ready to be claimed, calculate wait time based on the timer provided on the page
                matches = re.findall(r'(\d+)([hm])', wait_time_text)
                if matches:
                    total_time = sum(int(value) * (60 if unit == 'h' else 1) for value, unit in matches)
                    total_time += 1
                    total_time = max(5, total_time)  # Wait at least 5 minutes or the time
                    self.output(f"Step {self.step} - Not Time to claim this wallet yet. Wait for {total_time} minutes until the storage is filled.", 2)
                    return total_time
                else:
                    self.output(f"Step {self.step} - No wait time data found? Let's check again in one hour.", 2)
                    return 60  # Default wait time when no specific time until filled is found.
        except Exception as e:
            self.output(f"Step {self.step} - An unexpected error occurred: {e}", 1)
            return 60  # Default wait time in case of an unexpected error

    def get_balance(self, claimed=False):
        prefix = "After" if claimed else "Before"
        default_priority = 2 if claimed else 3

        # Dynamically adjust the log priority
        priority = max(self.settings['verboseLevel'], default_priority)

        # Construct the specific balance XPath
        balance_xpath = "//img[@alt='token']/following-sibling::p"

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


    def get_wait_time(self, step_number="108", beforeAfter="pre-claim", max_attempts=1):

        for attempt in range(1, max_attempts + 1):
            try:
                self.output(f"Step {self.step} - Get the wait time...", 3)
                xpath = "//div[p[text() = 'Storage']]/div[1]"
                elements = self.monitor_element(xpath, 10, "claim timer")
                # Replace occurrences of " h" with "h" and " m" with "m" (including the space)
                elements = elements.replace(" h ", "h ").replace(" m ", "m ")
                if elements:
                    return elements
                return False
            except Exception as e:
                self.output(f"Step {self.step} - An error occurred on attempt {attempt}: {e}", 3)
                return False

        # If all attempts fail         
        return False

def main():
    claimer = SeedClaimer()
    claimer.run()

if __name__ == "__main__":
    main()
