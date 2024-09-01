import os
import shutil
import sys
import time
import re
import json
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
import requests

from claimer import Claimer

class VertusClaimer(Claimer):
    def initialize_settings(self):
        super().initialize_settings()
        self.script = "games/vertus.py"
        self.prefix = "Vertus:"
        self.url = "https://web.telegram.org/k/#@vertus_app_bot"
        self.pot_full = "Filled"
        self.pot_filling = "to fill"
        self.seed_phrase = None
        self.forceLocalProxy = False
        self.forceRequestUserAgent = False
        self.step = "01"
        self.imported_seedphrase = None
        self.start_app_xpath = "//div[@class='reply-markup-row']//span[contains(text(),'Open app') or contains(text(), 'Play')]"

    def __init__(self):
        self.settings_file = "variables.txt"
        self.status_file_path = "status.txt"
        self.wallet_id = ""
        self.load_settings()
        self.random_offset = random.randint(self.settings['lowestClaimOffset'], self.settings['highestClaimOffset'])
        self.driver = None  # Initialize the driver to None
        super().__init__()

    def cipher_daily(self):
        cipher_xpath = "//div[contains(@class, 'btnLeft')]"
        self.move_and_click(cipher_xpath, 10, True, "move to the Cipher island link", self.step, "clickable")
        self.increase_step()
        
        xpaths = {
            '1': "//img[contains(@class, '_img_131qd_41') and @src='/icons/islands/farmIsland.png']",
            '2': "//img[contains(@class, '_img_131qd_41') and @src='/icons/islands/mineIsland.png']",
            '3': "//img[contains(@class, '_img_131qd_41') and @src='/icons/islands/buildIsland.png']",
            '4': "//img[contains(@class, '_img_131qd_41') and @src='/icons/islands/forestIsland.png']"
        }
        
        empty_slots_xpaths = "(//img[contains(@class, 'itemEmpty')])"
        
        if not self.move_and_click(empty_slots_xpaths, 10, False, "look for the first empty slot", self.step, "visible"):
            self.output(f"Step {self.step} - The daily puzzle is already completed.", 2)
            return
        else:
            self.output(f"Step {self.step} - Attempting to solve the daily puzzle.", 2)
            self.increase_step()
            
            try:
                response = requests.get('https://raw.githubusercontent.com/thebrumby/HotWalletClaimer/main/extras/vertuscipher')
                response.raise_for_status()
                sequence = response.text.strip()
            except requests.exceptions.RequestException as e:
                self.output(f"Error fetching the sequence: {e}", 2)
                return

            for i, digit in enumerate(sequence):
                n = i + 1
                xpath = xpaths.get(digit)
                check_xpath = f"{empty_slots_xpaths}[{n}]"

                if xpath:
                    # Move and click the element
                    self.move_and_click(xpath, 10, False, f"put digit {digit} in slot {n}", self.step, "visible")
                    
                    # Find the element and click it using JS
                    element = self.driver.find_element(By.XPATH, xpath)
                    self.driver.execute_script("arguments[0].click();", element)
                else:
                    self.output(f"Step {self.step} - No XPath found for digit {digit}", 2)

                # Increase the step counter
                self.increase_step()

        if not self.move_and_click(empty_slots_xpaths, 10, False, "double-check for puzzle completion", self.step, "visible"):
            self.output(f"Step {self.step} - The daily puzzle has been completed.", 2)
        else:
            self.output(f"Step {self.step} - The daily puzzle hasn't been solved, maybe we're waiting for a new solution.", 2)
            self.increase_step()

    def is_slot_filled(self, check_xpath):
        time.sleep(2)
        try:
            # Check if the element corresponding to check_xpath is no longer empty
            filled_element = self.driver.find_element(By.XPATH, check_xpath)
            if filled_element.is_displayed():
                self.output(f"Step {self.step} - Slot filled as expected for XPath: {check_xpath}", 3)
                return True
        except NoSuchElementException:
            self.output(f"Step {self.step} - Slot not filled, or element not found: {check_xpath}", 3)
            return False

        return False


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

    def check_daily_reward(self):
        action = ActionChains(self.driver)
        mission_xpath = "//p[contains(text(), 'Missions')]"
        self.move_and_click(mission_xpath, 10, False, "move to the missions link", self.step, "visible")
        success = self.click_element(mission_xpath)
        if success:
            self.output(f"Step {self.step} - Successfully able to click the 'Missions' link.", 3)
        else:
            self.output(f"Step {self.step} - Failed to click the 'Missions' link.", 3)
        self.increase_step()
        

        daily_xpath = "//p[contains(text(), 'Daily')]"
        self.move_and_click(daily_xpath, 10, False, "move to the daily missions link", self.step, "visible")
        success = self.click_element(daily_xpath)
        if success:
            self.output(f"Step {self.step} - Successfully able to click the 'Daily Missions' link.", 3)
        else:
            self.output(f"Step {self.step} - Failed to click the 'Daily Missions' link.", 2)
        self.increase_step()

        claim_xpath = "//p[contains(text(), 'Claim')]"
        button = self.move_and_click(claim_xpath, 10, False, "move to the claim daily missions link", self.step, "visible")
        if button:
            self.driver.execute_script("arguments[0].click();", button)
        success = self.click_element(claim_xpath)
        if success:
            self.increase_step()
            self.output(f"Step {self.step} - Successfully able to click the 'Claim Daily' link.", 3)
            return "Daily bonus claimed."

        come_back_tomorrow_xpath = "//p[contains(text(), 'Come back tomorrow')]"
        come_back_tomorrow_msg = self.move_and_click(come_back_tomorrow_xpath, 10, False, "check if the bonus is for tomorrow", self.step, "visible")
        if come_back_tomorrow_msg:
            self.increase_step()
            return "The daily bonus will be available tomorrow."

        self.increase_step()
        return "Daily bonus status unknown."

    def full_claim(self):
        self.step = "100"
        self.launch_iframe()

        xpath = "//p[text()='Collect']"
        island_text = ""
        button = self.move_and_click(xpath, 10, False, "collect the Island bonus (may not be present)", self.step, "visible")
        if button:
            self.driver.execute_script("arguments[0].click();", button)
            island_text = "Island bonus claimed."
        self.increase_step()    

        xpath = "//p[text()='Mining']"
        button = self.move_and_click(xpath, 10, False, "collect the Storage link", self.step, "visible")
        if button:
            self.driver.execute_script("arguments[0].click();", button)
        self.increase_step()

        balance_before_claim = self.get_balance(claimed=False)

        self.get_profit_hour(False)

        wait_time_text = self.get_wait_time(self.step, "pre-claim")
        self.output(f"Step {self.step} - Pre-Claim raw wait time text: {wait_time_text}", 3)

        if wait_time_text != "Ready to collect":
            matches = re.findall(r'(\d+)([hm])', wait_time_text)
            if matches:
                remaining_wait_time = (sum(int(value) * (60 if unit == 'h' else 1) for value, unit in matches)) + self.random_offset
                if remaining_wait_time < 5:
                    self.settings['forceClaim'] = True
                    self.output(f"Step {self.step} - the remaining time to claim is less than the random offset, so applying: settings['forceClaim'] = True", 3)
                if not self.settings["forceClaim"]:
                    remaining_wait_time = min(180, remaining_wait_time)
                    self.output(f"STATUS: {island_text}We'll go back to sleep for {remaining_wait_time} minutes.", 1)
                    return remaining_wait_time
            else:
                self.output("No matches found in wait_time_text, assigning a default wait time.", 2)
                return 60  # Default return if no matches found
                
        if not wait_time_text:
            return 60

        try:
            self.output(f"Step {self.step} - The pre-claim wait time is : {wait_time_text} and random offset is {self.random_offset} minutes.", 1)
            self.increase_step()

            if wait_time_text == "Ready to collect" or self.settings['forceClaim']:
                try:
                    xpath = "//div[p[text()='Collect']]"
                    self.move_and_click(xpath, 10, True, "collect the main reward", self.step, "clickable")
                    self.increase_step()

                    xpath = "//div[div/p[text()='Claim']]/div/p"
                    self.move_and_click(xpath, 10, True, "claim without connecting wallet (may not present)", self.step, "clickable")
                    self.increase_step()

                    # xpath = "//p[contains(@class, '_text_16x1w_17') and text()='Claim']"
                    # success = self.click_element(xpath)
                    # self.move_and_click(xpath, 10, True, "collect the 'splash' reward", self.step, "clickable")
                    # self.increase_step()

                    wait_time_text = self.get_wait_time(self.step, "post-claim")
                    self.output(f"Step {self.step} - Post-Claim raw wait time text: {wait_time_text}", 3)
                    matches = re.findall(r'(\d+)([hm])', wait_time_text)
                    total_wait_time = self.apply_random_offset(sum(int(value) * (60 if unit == 'h' else 1) for value, unit in matches))
                    self.increase_step()

                    balance_after_claim = self.get_balance(claimed=True)

                    self.cipher_daily() 

                    daily_reward_text = self.check_daily_reward()
                    self.increase_step()

                    if wait_time_text == "Ready to collect":
                        self.output(f"STATUS: The wait timer is still showing: Filled.", 1)
                        self.output(f"Step {self.step} - This means either the claim failed, or there is >4 minutes lag in the game.", 1)
                        self.output(f"Step {self.step} - We'll check back in 1 hour to see if the claim processed and if not try again.", 2)
                    else:
                        self.output(f"STATUS: {island_text}. Successful Claim & {daily_reward_text}", 1)
                    return min(180, total_wait_time)

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

    def get_profit_hour(self, claimed=False):
        prefix = "After" if claimed else "Before"
        default_priority = 2 if claimed else 3

        priority = max(self.settings['verboseLevel'], default_priority)

        # Construct the specific profit XPath
        profit_text = f'{prefix} PROFIT/HOUR:'
        profit_xpath = "(//p[@class='_descInfo_19xzr_38'])[last()]"

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

    def get_balance(self, claimed=False):
        prefix = "After" if claimed else "Before"
        default_priority = 2 if claimed else 3

        # Dynamically adjust the log priority
        priority = max(self.settings['verboseLevel'], default_priority)

        balance_text = f'{prefix} BALANCE:'
        balance_xpath = "//div[p[contains(text(), 'Vert balance')]]/div/p"

        try:
            balance_part = self.monitor_element(balance_xpath, 15, "balance")

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
                xpath = "//p[contains(@class, 'descInfo') and contains(text(), 'to')]"
                self.move_and_click(xpath, 10, False, f"get the {beforeAfter} wait timer", self.step, "visible")
                wait_time_element = self.monitor_element(xpath, 10, "claim timer")
                
                if wait_time_element is not None:
                    return wait_time_element
                else:
                    self.output(f"Step {step_number} - Attempt {attempt}: Wait time element not found. Clicking the 'Storage' link and retrying...", 3)
                    storage_xpath = "//h4[text()='Storage']"
                    self.move_and_click(storage_xpath, 30, True, "click the 'storage' link", f"{step_number} recheck", "clickable")
                    self.output(f"Step {step_number} - Attempted to select storage again...", 3)

            except TimeoutException:
                if attempt < max_attempts:
                    self.output(f"Step {step_number} - Attempt {attempt}: Wait time element not found. Clicking the 'Storage' link and retrying...", 3)
                    storage_xpath = "//h4[text()='Storage']"
                    self.move_and_click(storage_xpath, 30, True, "click the 'storage' link", f"{step_number} recheck", "clickable")
                else:
                    self.output(f"Step {step_number} - Attempt {attempt}: Wait time element not found.", 3)

            except Exception as e:
                self.output(f"Step {step_number} - An error occurred on attempt {attempt}: {e}", 3)

        return False

def main():
    claimer = VertusClaimer()
    claimer.run()

if __name__ == "__main__":
    main()
