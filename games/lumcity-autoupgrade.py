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

from lumcity import LumCityClaimer

class LumCityAUClaimer(LumCityClaimer):

    def initialize_settings(self):
        super().initialize_settings()
        self.script = "games/lumcity-autoupgrade.py"
        self.prefix = "LumCity-Auto:"
        self.allow_early_claim = False

    def __init__(self):
        super().__init__()
        self.start_app_xpath = "//span[contains(text(), 'Open the App')]"

    def attempt_upgrade(self, balance):
        
        try:
            # Get the current level using the new function
            current_level = self.get_current_level()
            
            # If the current level is greater than 20, return True, indicating no further upgrade needed
            upgrade_threshold = 40
            if current_level > upgrade_threshold:
                self.output(f"Step {self.step} - {current_level} > {upgrade_threshold} let's burn for Drop instead.", 2)
                return True
            else:
                self.output(f"Step {self.step} - {current_level} < {upgrade_threshold} so let's attempt to upgrade.", 2)
            
        except (ValueError, AttributeError, TypeError) as e:
            # Log the exception with a step number and a severity level of 2
            self.output(f"Step {self.step} - Unable to get the current level.", 2)
            return

        try:
            # Get the upgrade cost
            cost_upgrade = self.get_upgrade_cost()

        except (ValueError, AttributeError, TypeError) as e:
            # Log the exception with a step number and a severity level of 2
            self.output(f"Step {self.step} - Unable to convert cost or balance to a number.", 2)
            return

        shortfall = balance - cost_upgrade
        shortfall_text = f", Shortfall of {round(shortfall, 5)}" if shortfall < 0 else ""
        self.output(
            f"Step {self.step} - Balance: {balance}, Upgrade cost: {cost_upgrade}{shortfall_text}",
            2,
        )

        # Check if there is sufficient balance to upgrade
        if balance > cost_upgrade:
            self.output(f"Step {self.step} - We can upgrade, processing...", 2)
            self.perform_upgrade()
        else:
            # Log the insufficient balance with a step number and severity level of 2
            self.output(
                f"Step {self.step} - Not enough balance to upgrade. Cost: {cost_upgrade}, Balance: {balance}",
                2,
            )

        # Increment the step after attempting the upgrade
        self.increase_step()

    def get_upgrade_cost(self):
        
        cost_xpath = "(//div[contains(@class, '_price_lnqn0_57')]/span[1])[1]"

        try:
            # Attempt to locate and click on the upgrade cost element
            self.move_and_click(cost_xpath, 30, False, "look for cost upgrade", self.step, "visible")
            
            # Monitor the upgrade cost element for up to 15 seconds
            cost_upgrade = self.monitor_element(cost_xpath, 15, "cost of upgrade")

            if cost_upgrade is None:
                raise ValueError("Upgrade cost element not found")

            # Return the upgrade cost as a float, handling possible formatting issues
            return float(cost_upgrade.replace(',', '').strip())
        
        except Exception as e:
            self.output(f"Step {self.step} - Error retrieving upgrade cost: {e}", 2)
            return None
    
    def get_current_level(self):
        
        level_xpath = "//span[text()='pickaxe']/following-sibling::span"

        try:
            # Attempt to locate and click on the current level element
            self.move_and_click(level_xpath, 30, False, "look for current level", self.step, "visible")
            
            # Monitor the current level element for up to 15 seconds
            current_level = self.monitor_element(level_xpath, 15, "current level")

            if current_level is None:
                raise ValueError("Current level element not found")

            # Extract the level number from the text, assuming the format is ' / XX LVL '
            level_number = current_level.strip().split()[1]
            
            # Return the level number as an integer
            return int(level_number)
        
        except Exception as e:
            self.output(f"Step {self.step} - Error retrieving current level: {e}", 2)
            return None

    def perform_upgrade(self):
        
        try:
            # Define XPaths for the buttons
            buttons = {
                'Lvl Up': "//button[contains(@class, '_btn_16o80_16') and text()='Lvl Up']",
                'Confirm': "//button[contains(@class, '_btn_16o80_16') and text()='Confirm']",
                'Ok': "//button[contains(@class, '_btn_16o80_16') and text()='Ok']"
            }

            for action, xpath in buttons.items():
                self.move_and_click(xpath, 20, True, f"click the '{action}' button", self.step, "clickable")
                self.increase_step()

            self.output(f"STATUS: Upgrade performed successfully.", 1)
        
        except Exception as e:
            self.output(f"Step {self.step} - Unable to perform upgrade. Error: {e}", 2)


    def claim_drop(self, balance):
        try:
            # Click 'Participate white' button first
            self.move_and_click("//button[text()='Participate']", 10, True, "click the 'Participate white' button", self.step, "clickable")
            self.increase_step()

            # Attempt to click the 'Claim' button after 'Participate white'
            try:
                self.move_and_click(
                    "//button[contains(@class, '_btn_16o80_16') and contains(@class, '_btnTheme-primary_16o80_74') and contains(@class, '_btn_oc7tm_48')]",
                    10,
                    True,
                    "click the 'Claim' button",
                    self.step,
                    "clickable"
                )
            except Exception as e:
                self.output(f"Step {self.step} - 'Claim' button not found or not clickable", 2)
            self.increase_step()

            # Click 'Big participate blue' button
            self.move_and_click("//button[text()='Participate']", 10, True, "click the 'Big participate blue' button", self.step, "clickable")
            self.increase_step()

            # Obtain the GOLT balance
            xpath = "//div[contains(@class, 'yourCount')]"
            golt_text = self.monitor_element(xpath, 10, "get available GOLT")

            # Remove "GOLT Balance: " prefix
            golt_number_text = golt_text.replace("GOLT Balance: ", "").strip()

            # Split at the decimal point and take the integer part
            integer_part = golt_number_text.split('.')[0]

            # Remove commas
            golt_number = integer_part.replace(",", "")

            # If necessary, convert to integer
            golt_number = int(golt_number)
            self.output(f"Step {self.step} - Attempting to stake {golt_number} GOLT.", 2)

            # Locate the input field and enter the GOLT amount
            input_xpath = "//div[contains(@class, '_inputWrapper')]/input[contains(@class, '_burnInput')]"
            input_field = self.move_and_click(input_xpath, 10, True, "locate input field", self.step, "clickable")
            # Clear the input field before entering the new value
            input_field.clear()
            # Then send the new value one digit at a time
            for digit in str(golt_number):
                input_field.send_keys(digit)
                time.sleep(0.1)  # Optional: small delay between keystrokes
                screenshot_path = f"{self.screenshots_path}/{self.step}_Enter_Value_{digit}.png"
                self.driver.save_screenshot(screenshot_path)
            self.increase_step()

            # Click 'Burn' button
            self.move_and_click("//button[text()='Burn']", 10, True, "click the 'Burn' button", self.step, "clickable")
            self.increase_step()

            # Click 'OK' button
            self.move_and_click("//button[text()='Ok']", 10, True, "click the 'OK' button", self.step, "clickable")
            self.increase_step()

            # Click 'Back' button
            self.move_and_click("//button[contains(@class, 'backBtn')]", 10, True, "click the 'Back' button", self.step, "clickable")
            self.increase_step()

        except Exception as e:
            self.output(f"Step {self.step} - Error during drop claiming.", 2)
            
def main():
    claimer = LumCityAUClaimer()
    claimer.run()

if __name__ == "__main__":
    main()
