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

class YupalkaClaimer(Claimer):

    def initialize_settings(self):
        super().initialize_settings()
        self.script = "games/yupalka.py"
        self.prefix = "Yupalka:"
        self.url = "https://web.telegram.org/k/#@YupLand_bot"
        self.pot_full = "Filled"
        self.pot_filling = "to fill"
        self.box_claim = "Never."
        self.seed_phrase = None
        self.forceLocalProxy = False
        self.forceRequestUserAgent = False
        self.allow_early_claim = False
        self.start_app_xpath = "//div[contains(@class, 'new-message-bot-commands') and .//div[text()='Yupalka']]"

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

        # Open the driver and proceed to the game.
        self.launch_iframe()
        self.increase_step()

        # Get the original balance before the claim
        original_balance = self.get_balance(False)
        self.increase_step()

        # Check if there is a wait time
        remaining_wait_time = self.get_wait_time(self.step, False)
        self.increase_step()
        
        if remaining_wait_time:
            original_wait_time = remaining_wait_time
            modified_wait_time = self.apply_random_offset(original_wait_time)
            self.output(
                f"Step {self.step} - STATUS: Considering a wait time of {original_wait_time} minutes and applying an offset, we'll sleep for {modified_wait_time} minutes.", 
                1
            )
            return modified_wait_time

        # Claim the card
        self.click_random_card()
        self.increase_step()

        # Get the new balance after claiming
        new_balance = self.get_balance(True)
        self.increase_step()

        balance_diff = None  # Default in case balance difference can't be determined
        if new_balance:
            try:
                # Calculate the balance difference
                balance_diff = float(new_balance) - float(original_balance)
                if balance_diff > 0:
                    self.output(f"Step {self.step} - Making a claim increased the balance by {balance_diff}", 2)
            except Exception as e:
                self.output(f"Step {self.step} - Error calculating balance difference: {e}", 2)
            self.output(f"Step {self.step} - Main reward claimed.", 1)
        else:
            self.output(f"Step {self.step} - Claim appeared correct, but balance could not be validated.", 2)
        self.increase_step()

        # Check if there is a wait time (second wait)
        remaining_wait_time = self.get_wait_time(self.step, False)
        self.increase_step()

        self.attempt_upgrade()

        # Handle second wait time and output based on whether balance_diff was calculated
        if remaining_wait_time:
            original_wait_time = remaining_wait_time
            modified_wait_time = self.apply_random_offset(original_wait_time)

            if balance_diff is not None:
                # Balance difference was successfully calculated
                self.output(
                    f"STATUS: Claim successful, balance increased by {balance_diff}. We'll sleep for {modified_wait_time} minutes.", 
                    1
                )
            else:
                # Balance difference could not be validated
                self.output(
                    f"STATUS: Claim appeared correct, but we couldn't confirm the balance change. We'll sleep for {modified_wait_time} minutes.", 
                    1
                )
            return modified_wait_time

        # If no wait time, default to sleep for 60 minutes
        self.output(f"STATUS: We couldn't confirm the claim. Let's sleep for 60 minutes.", 1)
        return 60
        
    def click_random_card(self):
        # Define the base XPath for card fronts
        card_front_xpath = "//div[@class='c-home__card-front']"

        # Use WebDriverWait to wait until card elements are present
        wait = WebDriverWait(self.driver, 15)

        try:
            # Wait until the elements matching the XPath are located
            card_elements = wait.until(EC.presence_of_all_elements_located((By.XPATH, card_front_xpath)))

            # Check if we have card elements
            if card_elements:
                # Count the number of card fronts (total number of elements)
                total_cards = len(card_elements)

                # Randomly choose a card (0-based index for Selenium)
                chosen_card_index = random.randint(0, total_cards - 1)

                # Log the selected card and attempt to click on it
                self.output(f"Step {self.step} - Clicking on card {chosen_card_index + 1} of {total_cards}.", 2)

                # Perform the click action on the chosen card
                card_elements[chosen_card_index].click()

                return chosen_card_index + 1  # Returning 1-based index for consistency in logging
            else:
                self.output(f"Step {self.step} - No card fronts found.", 2)
                return None

        except TimeoutException:
            # Handle timeout if no card fronts are found within the time limit
            self.output(f"Step {self.step} - No card fronts found within the timeout period.", 2)
            return None

        except Exception as e:
            # Catch any other exceptions
            self.output(f"Step {self.step} - An error occurred while waiting for card fronts.", 2)
            return None

    def get_balance(self, claimed=False):
        prefix = "After" if claimed else "Before"
        default_priority = 2 if claimed else 3
        priority = max(self.settings['verboseLevel'], default_priority)
        
        balance_text = f"{prefix} BALANCE:"
        balance_xpath = "//div[@class='c-home__header-item-text']"  # Updated XPath
        
        try:
            # Monitor element with the new XPath
            element = self.monitor_element(balance_xpath, 15, "get balance")
            if element:
                balance_value = element.strip()
                
                try:
                    # Convert to float directly as it's just a number
                    balance_value = float(balance_value)
                    self.output(f"Step {self.step} - {balance_text} {balance_value}", priority)
                    return balance_value
                except ValueError:
                    self.output(f"Step {self.step} - Could not convert balance '{balance_value}' to a number.", priority)
                    return None
            else:
                self.output(f"Step {self.step} - Balance element not found.", priority)
                return None
        except Exception as e:
            self.output(f"Step {self.step} - An error occurred: {e}", priority)
            return None

    def get_wait_time(self, step_number="108", beforeAfter="pre-claim", max_attempts=1):
        for attempt in range(1, max_attempts + 1):
            try:
                self.output(f"Step {self.step} - Get the wait time...", 3)
                # Updated XPath to match the <p> tag containing the time
                xpath = "//div[@class='c-home__timer']/p"
                element = self.monitor_element(xpath, 10, "get claim timer")
                
                if element:
                    time_text = element.strip()  # Extract the time text (e.g., "19:42:26")
                    hh, mm, ss = map(int, time_text.split(':'))  # Split the time and convert to integers
                    
                    # Convert to total minutes
                    total_minutes = hh * 60 + mm + ss / 60
                    
                    self.output(f"Step {self.step} - Wait time is {total_minutes:.2f} minutes", 3)
                    return int(total_minutes)+1
                
                return False
            except Exception as e:
                self.output(f"Step {self.step} - An error occurred on attempt {attempt}: {e}", 3)
                return False

        return False

    def attempt_upgrade(self):
        pass

def main():
    claimer = YupalkaClaimer()
    claimer.run()

if __name__ == "__main__":
    main()