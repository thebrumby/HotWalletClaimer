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

class TabizooClaimer(Claimer):

    def initialize_settings(self):
        super().initialize_settings()
        self.script = "games/tabizoo.py"
        self.prefix = "TabiZoo:"
        self.url = "https://web.telegram.org/k/#@tabizoobot"
        self.pot_full = "Filled"
        self.pot_filling = "to fill"
        self.box_claim = "Never."
        self.seed_phrase = None
        self.forceLocalProxy = False
        self.forceRequestUserAgent = False
        self.allow_early_claim = False
        self.start_app_xpath = "//div[contains(@class, 'new-message-bot-commands') and .//div[text()='Start']]"
        self.start_app_menu_item = "//a[.//span[contains(@class, 'peer-title') and normalize-space(text())='TabiZoo']]"

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
            self.check_initial_screens()
            self.increase_step()
            self.set_cookies()

        except TimeoutException:
            self.output(f"Step {self.step} - Failed to find or switch to the iframe within the timeout period.", 1)

        except Exception as e:
            self.output(f"Step {self.step} - An error occurred: {e}", 1)

    def full_claim(self):
        self.step = "100"
    
        # Open the driver and proceed to the game.
        self.launch_iframe()
        self.increase_step()
    
        # Check the initial screens.
        self.check_initial_screens()
        self.increase_step()
    
        # Check the Daily rewards.
        self.click_daily_reward()
        self.increase_step()
    
        original_balance = self.get_balance(False)
        self.increase_step()
    
        xpath = "//span[contains(text(), 'Claim')]"
        success = self.brute_click(xpath, 10, "click the 'Claim' button")
        old_balance = self.get_balance(True)
        if success:
            try:
                balance_diff = float(old_balance) - float(original_balance)
                if balance_diff > 0:
                    self.output(f"Step {self.step} - Making a claim increased the balance by {balance_diff}", 2)
            except Exception as e:
                pass
            self.output(f"Step {self.step} - Main reward claimed.", 1)
        self.increase_step()
    
        # Retrieve profit per hour for logging (if needed)
        self.get_profit_hour(True)
    
        try:
            # Get the wait time in minutes directly from the new function.
            wait_time_minutes = self.get_wait_time(self.step, "post-claim")
            
            # Try the slots game.
            self.play_spins()
            balance = self.get_balance(True)
            try:
                balance_diff = float(balance) - float(old_balance)
                if balance_diff > 0:
                    self.output(f"Step {self.step} - Playing slots increased the balance by {balance_diff}", 2)
            except Exception as e:
                pass
    
            # Go back to the home page.
            xpath = "(//div[normalize-space(.) = 'Shiro'])[1]"
            self.move_and_click(xpath, 10, True, "click the 'Home' tab", self.step, "clickable")
    
            # Try to upgrade the level if auto-upgrade is enabled.
            self.attempt_upgrade(balance)
    
            if wait_time_minutes:
                wait_time_minutes = self.apply_random_offset(wait_time_minutes)
                self.output(f"STATUS: We'll go back to sleep for {wait_time_minutes:.2f} minutes.", 1)
                return wait_time_minutes
    
        except Exception as e:
            self.output(f"Step {self.step} - An unexpected error occurred: {e}", 1)
            return 60
    
        self.output(f"STATUS: We seemed to have reached the end without confirming the action!", 1)
        return 60

    def play_spins(self):
        return
        xpath_spin_tab = "(//div[normalize-space(.) = 'Spin'])[1]"
        xpath_spin_button = "//img[contains(@src, 'spin_btn')]"

        # Attempt to click the 'Spin' tab
        success = self.move_and_click(xpath_spin_tab, 10, True, "click the 'Spin' tab", self.step, "clickable")
        if not success:
            self.quit_driver()
            self.launch_iframe()
            success = self.brute_click(xpath_spin_tab, 10, "click the 'Spin' tab")
            if not success:
                self.output(f"Step {self.step} - It seems the sequence to play the slot machine failed.", 2)
                return

        self.brute_click(xpath_spin_button, 60, "spin the reels")
        
    def click_daily_reward(self):
        # Check the Daily rewards.
        xpath = "//div[contains(@class, 'bg-[#FF5C01]') and contains(@class, 'rounded-full') and contains(@class, 'w-[8px]') and contains(@class, 'h-[8px]')]"
        success = self.move_and_click(xpath, 10, False, "check if the daily reward can be claimed (may not be present)", self.step, "clickable")
        if not success:
            self.output(f"Step {self.step} - The daily reward appears to have already been claimed.", 2)
            self.increase_step()
            return
        xpath = "//img[contains(@src, 'task_icon')]"
        success = self.brute_click(xpath, 10, "click the 'Check Login' tab")
        self.increase_step()

        xpath = "//h4[contains(text(), 'Daily Reward')]"
        success = self.brute_click(xpath, 10, "click the 'Daily Reward' button")
        self.increase_step()

        xpath = "//div[contains(text(), 'Claim')]"
        success = self.brute_click(xpath, 10, "claim the 'Daily Reward'")
        self.increase_step()

        xpath = "//div[contains(text(), 'Come Back Tomorrow')]"
        success = self.move_and_click(xpath, 10, False, "check for 'Come Back Tomorrow'", self.step, "visible")
        self.increase_step()

        if not success:
            self.output(f"Step {self.step}: It seems the sequence to claim the daily reward failed.", 2)
            return

        self.output(f"STATUS: Successfully claimed the daily reward.", 2)

        self.quit_driver()
        self.launch_iframe()

    def check_initial_screens(self):
        # First 'Next Step' button
        xpath = "//div[normalize-space(text())='Go']"
        self.move_and_click(xpath, 10, True, "click the 'Go' button", self.step, "clickable")
        self.output(f"Step {self.step} - You have already cleared the initial screens.", 2)
        self.increase_step()
        
    def get_balance(self, claimed=False):
        prefix = "After" if claimed else "Before"
        default_priority = 2 if claimed else 3
    
        priority = max(self.settings['verboseLevel'], default_priority)
    
        balance_text = f'{prefix} BALANCE:' if claimed else f'{prefix} BALANCE:'
        # Updated xpath: select the <div> that is a following-sibling of the <img> with 'coin_icon' in its src.
        balance_xpath = "//img[contains(@src, 'coin_icon')]/following-sibling::div"
    
        try:
            element = self.monitor_element(balance_xpath, 15, "get balance")
            if element:
                balance_part = element.strip()
                multiplier = 1  # Default multiplier
    
                # Check for 'K' or 'M' and adjust the multiplier
                if balance_part.endswith('K'):
                    multiplier = 1_000
                    balance_part = balance_part[:-1]  # Remove the 'K'
                elif balance_part.endswith('M'):
                    multiplier = 1_000_000
                    balance_part = balance_part[:-1]  # Remove the 'M'
    
                try:
                    balance_value = float(balance_part) * multiplier
                    self.output(f"Step {self.step} - {balance_text} {balance_value}", priority)
                    return balance_value
                except ValueError:
                    self.output(f"Step {self.step} - Could not convert balance '{balance_part}' to a number.", priority)
                    return None
    
        except NoSuchElementException:
            self.output(f"Step {self.step} - Element containing '{prefix} Balance:' was not found.", priority)
        except Exception as e:
            self.output(f"Step {self.step} - An error occurred: {str(e)}", priority)
    
        self.increase_step()

    def get_wait_time(self, step_number="108", beforeAfter="pre-claim", max_attempts=1):
        return 180

    def get_profit_hour(self, claimed=False):
        """
        Retrieves the profit per hour as a float by extracting the value from the profit element.
        """
        import re
        prefix = "After" if claimed else "Before"
        default_priority = 2 if claimed else 3
        priority = max(self.settings['verboseLevel'], default_priority)
    
        # Updated XPath: locate the span with a leading '+' following the Mining Rate label.
        profit_xpath = "//label[normalize-space(text())='Mining Rate']/following-sibling::div//span[starts-with(normalize-space(text()), '+')]"
        try:
            profit_text = self.monitor_element(profit_xpath, 15, "profit per hour")
            if profit_text:
                # Remove any non-numeric characters (like the '+' sign)
                profit_clean = re.sub(r"[^\d.]", "", profit_text)
                profit_value = float(profit_clean)
                self.output(f"Step {self.step} - {prefix} PROFIT/HOUR: {profit_value}", priority)
                return profit_value
        except NoSuchElementException:
            self.output(f"Step {self.step} - Element containing '{prefix} Profit/Hour:' was not found.", priority)
        except Exception as e:
            self.output(f"Step {self.step} - An error occurred: {str(e)}", priority)
        
        self.increase_step()
        return None

    def attempt_upgrade(self, balance):
        pass

def main():
    claimer = TabizooClaimer()
    claimer.run()

if __name__ == "__main__":
    main()
