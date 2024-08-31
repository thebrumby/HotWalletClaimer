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

class OxygenClaimer(Claimer):

    def initialize_settings(self):
        super().initialize_settings()
        self.script = "games/oxygen.py"
        self.prefix = "Oxygen:"
        self.url = "https://web.telegram.org/k/#@oxygenminerbot"
        self.pot_full = "Filled"
        self.pot_filling = "to fill"
        self.box_claim = "Never."
        self.seed_phrase = None
        self.forceLocalProxy = False
        self.forceRequestUserAgent = False
        self.allow_early_claim = False
        self.start_app_xpath = "//div[contains(@class, 'reply-markup-row')]//button[.//span[contains(text(), 'Start App')] or .//span[contains(text(), 'Play Now!')]]"

    def __init__(self):
        self.settings_file = "variables.txt"
        self.status_file_path = "status.txt"
        self.wallet_id = ""
        self.load_settings()  # Load settings before initializing other attributes
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
            self.set_cookies()

        except TimeoutException:
            self.output(f"Step {self.step} - Failed to find or switch to the iframe within the timeout period.", 1)

        except Exception as e:
            self.output(f"Step {self.step} - An error occurred: {e}", 1)

    def full_claim(self):
        self.step = "100"

        self.launch_iframe()
        self.increase_step()

        xpath = "//div[contains(text(),'Get reward')]"
        self.move_and_click(xpath, 10, True, "click the opening 'Get Reward' button (may not be present)", self.step, "clickable")
        self.increase_step()

        self.get_balance(False)
        self.increase_step()

        self.output(f"Step {self.step} - The last lucky box claim was attempted on {self.box_claim}.", 2)
        self.increase_step()

        wait_time_text = self.get_wait_time(self.step, "pre-claim")

        if not wait_time_text:
            return 60

        if wait_time_text != self.pot_full:
            matches = re.findall(r'(\d+)([hm])', wait_time_text)
            remaining_wait_time = (sum(int(value) * (60 if unit == 'h' else 1) for value, unit in matches))
            remaining_wait_time = self.apply_random_offset(remaining_wait_time)
            if remaining_wait_time < 5 or self.settings["forceClaim"]:
                self.settings['forceClaim'] = True
                self.output(f"Step {self.step} - the remaining time to claim is less than the random offset, so applying: settings['forceClaim'] = True", 3)
            else:
                self.output(f"STATUS: Considering {wait_time_text}, we'll go back to sleep for {remaining_wait_time} minutes.", 1)
                return remaining_wait_time

        try:
            self.output(f"Step {self.step} - The pre-claim wait time is : {wait_time_text} and random offset is {self.random_offset} minutes.", 1)
            self.increase_step()

            if wait_time_text == self.pot_full or self.settings['forceClaim']:
                try:
                    xpath = "//div[@class='farm_btn']"
                    button = self.brute_click(xpath, 10, "click the 'Claim' button")
                    self.increase_step()

                    self.output(f"Step {self.step} - Waiting 10 seconds for the totals and timer to update...", 3)
                    time.sleep(10)

                    wait_time_text = self.get_wait_time(self.step, "post-claim")
                    matches = re.findall(r'(\d+)([hm])', wait_time_text)

                    calculated_time = sum(int(value) * (60 if unit == 'h' else 1) for value, unit in matches)
                    random_offset = self.apply_random_offset(calculated_time)
                    total_wait_time = random_offset if random_offset > calculated_time else calculated_time

                    self.increase_step()
                    self.click_daily_buttons()
                    self.get_balance(True)
                    self.get_profit_hour(True)
                    self.increase_step()

                    self.output(f"Step {self.step} - check if there are lucky boxes..", 3)
                    xpath = "//div[@class='boxes_cntr']"
                    boxes = self.monitor_element(xpath,15,"lucky boxes")
                    self.output(f"Step {self.step} - Detected there are {boxes} boxes to claim.", 3)
                    if boxes:  # This will check if boxes is not False
                        self.output(f"Step {self.step} - Detected there are {boxes} boxes to claim.", 3)
                        if boxes.isdigit() and int(boxes) > 0:
                            xpath = "//div[@class='boxes_d_wrap']"
                            self.move_and_click(xpath, 10, True, "click the boxes button", self.step, "clickable")
                            xpath = "//div[@class='boxes_d_open' and contains(text(), 'Open box')]"
                            box = self.move_and_click(xpath, 10, True, "open the box...", self.step, "clickable")
                            if box:
                                self.box_claim = datetime.now().strftime("%d %B %Y, %I:%M %p")
                                self.output(f"Step {self.step} - The date and time of the box claim has been updated to {self.box_claim}.", 3)
                        else:
                            self.output(f"Step {self.step} - No valid number of boxes detected or zero boxes.", 3)
                    else:
                        self.output(f"Step {self.step} - No elements found for boxes.", 3)
                        
                    if wait_time_text == self.pot_full:
                        self.output(f"STATUS: The wait timer is still showing: Filled.", 1)
                        self.output(f"Step {self.step} - This means either the claim failed, or there is lag in the game.", 1)
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
        
    def click_daily_buttons(self, wait_time=10, timeout=10):
        try:
            # Click the first button
            xpath_first_button = "//div[@class='daily_btn_wrap']"
            self.move_and_click(xpath_first_button, timeout, True, "click 'daily_btn_wrap'", self.step, "clickable")

            # Click the second button
            xpath_second_button = "//div[@class='daily_get' and contains(text(), 'Get reward')]"
            self.move_and_click(xpath_second_button, timeout, True, "click 'Get reward'", self.step, "clickable")

            # Check if the reward has been claimed
            xpath_reward_message = "//div[contains(text(), 'You have already claimed this reward')]"
            if self.move_and_click(xpath_reward_message, timeout, False, "check if already claimed", self.step, "visible"):
                self.output(f"Step {self.step} - Daily reward already claimed.", 2)

            # Click close
            xpath_close_button = "//div[@class='page_close']"
            self.move_and_click(xpath_close_button, timeout, True, "click close the tab", self.step, "clickable")

            return True

        except Exception as e:
            self.output(f"Error during clicking daily buttons: {e}", 1)
            return False
            
    def get_balance(self, claimed=False):
        prefix = "After" if claimed else "Before"
        default_priority = 2 if claimed else 3

        priority = max(self.settings['verboseLevel'], default_priority)

        balance_text = f'{prefix} BALANCE:'

        try:
            oxy_balance_xpath = "//span[@class='oxy_counter']"
            food_balance_xpath = "//div[@class='indicator_item i_food' and @data='food']/div[@class='indicator_text']"
            oxy_balance = float(self.monitor_element(oxy_balance_xpath,15,"oxygen balance"))
            food_balance = float(self.monitor_element(food_balance_xpath,15,"food balance"))

            self.output(f"Step {self.step} - {balance_text} {oxy_balance:.0f} O2, {food_balance:.0f}  food", priority)

        except NoSuchElementException:
            self.output(f"Step {self.step} - Element containing '{prefix} Balance:' was not found.", priority)
        except Exception as e:
            self.output(f"Step {self.step} - An error occurred: {str(e)}", priority)

        self.increase_step()

    def get_wait_time(self, step_number="108", beforeAfter="pre-claim", max_attempts=1):
        for attempt in range(1, max_attempts + 1):
            try:
                            
                # Step 1: Check for the "Collect food" button
                xpath_collect = "//div[@class='farm_btn']"
                elements_collect = self.monitor_element(xpath_collect, 10, "check if the pot is full")
                if isinstance(elements_collect, str) and re.search(r"[СC]ollect food", elements_collect, re.IGNORECASE):
                    return self.pot_full
            
                # Step 2: Check for the wait time element
                xpath_wait = "//div[@class='farm_wait']"
                elements_wait = self.monitor_element(xpath_wait, 10, "check the remaining time")
                if elements_wait:
                    return elements_wait
            
                return False
        
            except TypeError as e:
                self.output(f"Step {self.step} - TypeError on attempt {attempt}: {e}", 3)
                return False
        
            except Exception as e:
                self.output(f"Step {self.step} - An error occurred on attempt {attempt}: {e}", 3)
                return False

        return False

    def get_profit_hour(self, claimed=False):
        prefix = "After" if claimed else "Before"
        default_priority = 2 if claimed else 3

        priority = max(self.settings['verboseLevel'], default_priority)

        # Construct the specific profit XPath
        profit_text = f'{prefix} PROFIT/HOUR:'
        profit_xpath = "//span[@id='oxy_coef']"

        try:
            element = self.strip_non_numeric(self.monitor_element(profit_xpath,15,"profit per hour"))

            # Check if element is not None and process the profit
            if element:
                element = float(element)*3600
                self.output(f"Step {self.step} - {profit_text} {element}", priority)

        except NoSuchElementException:
            self.output(f"Step {self.step} - Element containing '{prefix} Profit/Hour:' was not found.", priority)
        except Exception as e:
            self.output(f"Step {self.step} - An error occurred: {str(e)}", priority)  # Provide error as string for logging
        
        self.increase_step()

def main():
    claimer = OxygenClaimer()
    claimer.run()

if __name__ == "__main__":
    main()
