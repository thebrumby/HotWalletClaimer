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

class BlumClaimer(Claimer):

    def initialize_settings(self):
        super().initialize_settings()
        self.script = "games/blum.py"
        self.prefix = "Blum:"
        self.url = "https://web.telegram.org/k/#@BlumCryptoBot"
        self.pot_full = "Filled"
        self.pot_filling = "to fill"
        self.seed_phrase = None
        self.forceLocalProxy = True
        self.forceRequestUserAgent = False
        self.allow_early_claim = False
        self.start_app_xpath = "//button[span[contains(text(), 'Launch Blum')]]"

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

            self.set_cookies()

        except TimeoutException:
            self.output(f"Step {self.step} - Failed to find or switch to the iframe within the timeout period.", 1)

        except Exception as e:
            self.output(f"Step {self.step} - An error occurred: {e}", 1)

    def full_claim(self):
        self.step = "100"

        self.launch_iframe()

        xpath = "//span[contains(text(), 'Your daily rewards')]"
        present = self.move_and_click(xpath, 20, False, "check for daily reward", self.step, "visible")
        self.increase_step()
        reward_text = None
        if present:
            xpath = "(//div[@class='count'])[1]"
            points = self.move_and_click(xpath, 10, False, "get daily points", self.step, "visible")
            xpath = "(//div[@class='count'])[2]"
            days = self.move_and_click(xpath, 10, False, "get consecutive days played", self.step, "visible")
            reward_text = f"Daily rewards: {points.text} points & {days.text} days."
            xpath = "//button[.//span[text()='Continue']]"
            self.move_and_click(xpath, 10, True, "click continue", self.step, "clickable")
            self.increase_step()

        xpath = "//button[.//div[text()='Continue']]"
        self.move_and_click(xpath, 10, True, "click continue", self.step, "clickable")
        self.increase_step()

        xpath = "//button[.//span[contains(text(), 'Start farming')]][1]"
        self.move_and_click(xpath, 10, True, "click the 'Start farming' button (may not be present)", self.step, "clickable")
        # self.click_element(xpath)
        self.increase_step()

        self.get_balance(False)

        wait_time_text = self.get_wait_time(self.step, "pre-claim") 

        if not wait_time_text:
            return 60

        if wait_time_text != self.pot_full:
            matches = re.findall(r'(\d+)([hm])', wait_time_text)
            remaining_wait_time = (sum(int(value) * (60 if unit == 'h' else 1) for value, unit in matches)) + self.random_offset
            if remaining_wait_time < 5 or self.settings["forceClaim"]:
                self.settings['forceClaim'] = True
                self.output(f"Step {self.step} - the remaining time to claim is less than the random offset, so applying: settings['forceClaim'] = True", 3)
            else:
                self.output(f"STATUS: Still {wait_time_text} and {self.random_offset} minute offset - Let's sleep. {reward_text}", 1)
                return remaining_wait_time

        try:
            self.output(f"Step {self.step} - The pre-claim wait time is : {wait_time_text} and random offset is {self.random_offset} minutes.", 1)
            self.increase_step()

            if wait_time_text == self.pot_full or self.settings['forceClaim']:
                try:
                    xpath = "//button[.//div[contains(text(), 'Claim')]]"
                    self.move_and_click(xpath, 10, True, "click the 'Claim' button", self.step, "clickable")
                    self.increase_step()

                    time.sleep(5)

                    xpath = "//button[.//span[contains(text(), 'Start farming')]][1]"
                    self.move_and_click(xpath, 10, True, "click the 'Start farming' button", self.step, "clickable")
                    self.increase_step()

                    self.output(f"Step {self.step} - Waiting 10 seconds for the totals and timer to update...", 3) 
                    time.sleep(10)
                    
                    wait_time_text = self.get_wait_time(self.step, "post-claim") 
                    matches = re.findall(r'(\d+)([hm])', wait_time_text)
                    total_wait_time = self.apply_random_offset(sum(int(value) * (60 if unit == 'h' else 1) for value, unit in matches))
                    self.increase_step()

                    self.get_balance(True)

                    if wait_time_text == self.pot_full:
                        self.output(f"Step {self.step} - The wait timer is still showing: Filled.", 1)
                        self.output(f"Step {self.step} - This means either the claim failed, or there is >4 minutes lag in the game.", 1)
                        self.output(f"Step {self.step} - We'll check back in 1 hour to see if the claim processed and if not try again.", 2)
                    else:
                        self.output(f"STATUS: Post claim wait time: {wait_time_text} & new timer = {total_wait_time} minutes. {reward_text}", 1)
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
        balance_xpath = f"//div[@class='balance']//div[@class='kit-counter-animation value']"

        try:
            balance_element = WebDriverWait(self.driver, 10).until(
                EC.visibility_of_element_located((By.XPATH, balance_xpath))
            )

            if balance_element:
                char_elements = balance_element.find_elements(By.XPATH, ".//div[@class='el-char']")
                balance_part = ''.join([char.text for char in char_elements]).strip()
                
                self.output(f"Step {self.step} - {balance_text} {balance_part}", priority)

        except NoSuchElementException:
            self.output(f"Step {self.step} - Element containing '{prefix} Balance:' was not found.", priority)
        except Exception as e:
            self.output(f"Step {self.step} - An error occurred: {str(e)}", priority) 

        self.increase_step()

    def get_wait_time(self, step_number="108", beforeAfter="pre-claim", max_attempts=1):
        for attempt in range(1, max_attempts + 1):
            try:
                self.output(f"Step {self.step} - First check if the time is still elapsing...", 3)
                xpath = "//div[@class='time-left']"
                wait_time_value = self.monitor_element(xpath, 10, "wait timer pot elapsing")
                if wait_time_value:
                    return wait_time_value

                self.output(f"Step {self.step} - Then check if the pot is full...", 3)
                xpath = "//button[.//div[contains(text(), 'Claim')]]"
                pot_full_value = self.monitor_element(xpath, 10, "wait timer pot full")
                if pot_full_value:
                    return self.pot_full
                return False
            except Exception as e:
                self.output(f"Step {self.step} - An error occurred on attempt {attempt}: {e}", 3)
                return False

        return False

def main():
    claimer = BlumClaimer()
    claimer.run()

if __name__ == "__main__":
    main()