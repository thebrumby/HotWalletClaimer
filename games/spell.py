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

class SpellClaimer(Claimer):

    def initialize_settings(self):
        super().initialize_settings()
        self.script = "games/spell.py"
        self.prefix = "Spell:"
        self.url = "https://web.telegram.org/k/#@spell_wallet_bot"
        self.pot_full = "Filled"
        self.pot_filling = "to fill"
        self.seed_phrase = None
        self.forceLocalProxy = False
        self.forceRequestUserAgent = False
        self.start_app_xpath = "//div[@class='reply-markup-row']//span[contains(text(),'Open Spell')]"

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
            xpath = "//*[contains(text(), 'Roadmap')]"
            self.target_element = self.move_and_click(xpath, 30, False, "wait until 'Roadmap' disappears (may not be present)", self.step, "invisible")
            self.increase_step()

            # Then look for the seed phase textarea:
            xpath = "//textarea[@placeholder='Seed Phrase']"
            input_field = self.move_and_click(xpath, 30, True, "locate seedphrase textbox", self.step, "clickable")
            if not self.imported_seedphrase:
                self.imported_seedphrase = self.validate_seed_phrase()
            input_field.send_keys(self.imported_seedphrase) 
            self.output(f"Step {self.step} - Was successfully able to enter the seed phrase...",3)
            self.increase_step()

            # Click the continue button after seed phrase entry:
            recover_wallet_xpath = "//button[contains(text(), 'Recover Wallet')]"
            wallet_check_xpath = "//p[contains(text(), 'Wallet')]"
            start_time = time.time()
            timeout = 60  # seconds

            while time.time() - start_time < timeout:
                if self.move_and_click(recover_wallet_xpath, 10, False, "check for success", self.step, "visible"):
                    self.click_element(recover_wallet_xpath, 30, "Click 'Recover Wallet'")
                    if self.move_and_click(wallet_check_xpath, 10, False, "check if wallet tab visible (may not be present)", "08", "visible"):
                        self.output(f"Step {self.step} - The wallet tab is now visible...",3)
                        break  # Exit loop if the Wallet check element is found

            self.increase_step()

            # Final Housekeeping
            self.set_cookies()

        except TimeoutException:
            self.output(f"Step {self.step} - Failed to find or switch to the iframe within the timeout period.",1)

        except Exception as e:
            self.output(f"Step {self.step} - An error occurred: {e}",1)

    def full_claim(self):
        self.step = "100"

        self.launch_iframe()

        xpath = "//*[contains(text(), 'Roadmap')]"
        self.target_element = self.move_and_click(xpath, 30, False, "wait until 'Roadmap' disappears (may not be present)", self.step, "invisible")
        self.increase_step()

        self.get_balance(False)

        # Click on the Storage link:
        xpath = "//p[contains(text(), 'Claim')]"
        if self.move_and_click(xpath, 10, True, "click the 'Claim' link", self.step, "clickable"):
            self.output(f"Step {self.step} - Claim was available and clicked.", 3)
            self.increase_step()
            success_text="Claim attempted. "
            self.increase_step()
        xpath = "//*[contains(text(), 'Got it')]"
        self.move_and_click(xpath, 10, True, "check for 'Got it' message (may not be present)", self.step, "clickable")
        self.increase_step()

        try:
            # Calculate the remaining time in hours
            hourly_profit = float(self.get_profit_hour(True))
    
            xpath = "//div[@id='slider-root-:r5:']/following-sibling::p"
            elapsed = self.monitor_element(xpath, 10, "Get the timer bar")
    
            # Split elapsed into current and max
            current, max_value = map(float, elapsed.split('/'))
    
            # Perform the calculation
            remaining_time_hours = (max_value - current) / hourly_profit
    
            # Convert the remaining time to minutes
            theoretical_timer = remaining_time_hours * 60
        except Exception as e:
            # If there's an error, assign a default value of 60 minutes
            print(f"An error occurred: {e} - Assigning 1 hour timer")
            theoretical_timer = 60

        self.get_balance(True)

        theoretical_timer_rounded = round(theoretical_timer, 1)
        modified_timer = self.apply_random_offset(theoretical_timer)
        modified_timer_rounded = round(modified_timer, 1)

        self.output(f"STATUS: {success_text}Claim again in {modified_timer_rounded} minutes (originally {theoretical_timer_rounded})", 3)
        return int(modified_timer)

    def get_balance(self, claimed=False):

        prefix = "After" if claimed else "Before"
        default_priority = 2 if claimed else 3

        # Dynamically adjust the log priority
        priority = max(self.settings['verboseLevel'], default_priority)

        # Construct the specific balance XPath
        balance_text = f'{prefix} BALANCE:' if claimed else f'{prefix} BALANCE:'
        balance_xpath = f"//h2[text()='Mana Balance']/following-sibling::h2[1]"

        try:
            element = self.strip_html_and_non_numeric(self.monitor_element(balance_xpath, 15, "get balance"))

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

        priority = max(self.settings['verboseLevel'], default_priority)

        # Construct the specific profit XPath
        profit_text = f'{prefix} PROFIT/HOUR:'
        profit_xpath = "//p[contains(text(), 'Mana per hour:')]/following-sibling::p[1]"

        try:
            element = self.strip_non_numeric(self.monitor_element(profit_xpath, 15, "profit per hour"))

            # Check if element is not None and process the profit
            if element:
                self.output(f"Step {self.step} - {profit_text} {element}", priority)
                return element
            return None
        except NoSuchElementException:
            self.output(f"Step {self.step} - Element containing '{prefix} Profit/Hour:' was not found.", priority)
        except Exception as e:
            self.output(f"Step {self.step} - An error occurred: {str(e)}", priority)  # Provide error as string for logging
        return None
        self.increase_step()

def main():
    claimer = SpellClaimer()
    claimer.run()

if __name__ == "__main__":
    main()