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

        # Open the driver and proced to the game.
        self.launch_iframe()
        self.increase_step()

        # Check the Daily rewards.
        self.check_initial_screens()
        self.increase_step()

        # Check the Daily rewards.
        self.click_daily_reward()
        self.increase_step()

        self.get_balance(False)
        self.increase_step()

        xpath = "//div[@class='claim']/p[text()='Claim']"
        success = self.move_and_click(xpath, 10, True, "click the main 'Claim' button...", self.step, "clickable")
        if success:
            # Confirm success
            xpath = "//div[@class='theme-button']/p[contains(text(), 'Confirm')]"
            success = self.move_and_click(xpath, 10, True, "confirm the main claim...", self.step, "clickable")
            if success:
                self.output(f"Step {self.step} - Main reward claimed.", 1)
                self.get_balance(True)
        self.increase_step()


        self.get_profit_hour(True)
        self.attempt_upgrade()

        try:
            wait_time_text = self.get_wait_time(self.step, "post-claim")

            if wait_time_text:
                matches = re.findall(r'(\d+)([hm])', wait_time_text)
                remaining_wait_time = (sum(int(value) * (60 if unit == 'h' else 1) for value, unit in matches))
                remaining_wait_time = self.apply_random_offset(remaining_wait_time)
                self.output(f"STATUS: Considering {wait_time_text}, we'll go back to sleep for {remaining_wait_time} minutes.", 1)
                return remaining_wait_time

        except Exception as e:
            self.output(f"Step {self.step} - An unexpected error occurred: {e}", 1)
            return 60
        self.output(f"STATUS: We seemed to have reached the end without confirming the action!", 1)
        return 60
        
    def click_daily_reward(self):
        # Check the Daily rewards.
        xpath = "//div[@class='check-in']"
        success = self.move_and_click(xpath, 10, True, "check in...", self.step, "clickable")
        if success:
            # And make the claim.
            xpath = "//div[@class='theme-button']/p[contains(text(), 'Claim')]"
            success = self.move_and_click(xpath, 10, True, "claim daily reward", self.step, "clickable")
            if success:
                # And confirm success.
                xpath = "//div[@class='theme-button']/p[contains(text(), 'Confirm')]"
                success = self.move_and_click(xpath, 10, True, "confirm daily reward", self.step, "clickable")
                if success:
                    self.output(f"Step {self.step} - Successfully claimed the daily reward.", 2)
        else:
            self.output(f"Step {self.step} - The daily reward appears to have already been claimed.", 2)

    def check_initial_screens(self):
        # Check for the initial screens.
        xpath_claim_now = "//div[@class='theme-button claim-btn']/p[contains(text(), 'Claim Now')]"
        success = self.move_and_click(xpath_claim_now, 10, True, "see if we need to complete initial screens", self.step, "clickable")
        if success:
            self.increase_step()

            # First 'Next Step' button
            xpath_next_step_first = "(//div[@class='theme-button next-btn']/p[contains(text(), 'Next Step')])[1]"
            success = self.move_and_click(xpath_next_step_first, 10, True, "move to 'Next Step'", self.step, "clickable")
            if success:
                self.increase_step()

                # Combined 'go' and 'check' button functionality
                combined_success = self.click_go_and_check_buttons()
                if combined_success:
                    self.increase_step()

                    # Remove 'disable' class from the second 'Next Step' button
                    xpath_parent_button = "//div[@class='theme-button next-btn disable']"
                    self.remove_disable_class(xpath_parent_button)

                    xpath_child_button = "(//p[contains(text(), 'Next Step')])[2]"
                    # Second 'Next Step' button
                    success = self.move_and_click(xpath_child_button, 20, True, "move to 'Next Step' again", self.step, "clickable")
                    self.move_and_click(xpath_child_button, 20, True, "move to 'Next Step' again (may not be present)", self.step, "clickable")
                    if success:
                        self.increase_step()

                        # 'Get More' button
                        xpath_get_more = "//div[@class='theme-button get-more-btn']/p[contains(text(), 'Get More')]"
                        success = self.move_and_click(xpath_get_more, 10, True, "'Get More'", self.step, "clickable")
                        self.increase_step()
        else:
            self.output(f"Step {self.step} - You have already cleared the initial screens.", 2)
            self.increase_step()

    def remove_disable_class(self, xpath):
        try:
            # Wait for the element to be present and fully loaded
            element = WebDriverWait(self.driver, 10).until(EC.presence_of_element_located((By.XPATH, xpath)))

            # Directly remove the 'disable' class from the element
            self.driver.execute_script("arguments[0].classList.remove('disable');", element)

            self.output(f"Step {self.step} - Removed 'disable' class from element matching: {xpath}", 3)
        except Exception as e:
            if self.settings['debugIsOn']:
                self.output(f"Step {self.step} - Could not remove 'disable' class:", 3)

    def click_go_and_check_buttons(self):
        original_window = self.driver.current_window_handle
        go_success = False
        check_success = False

        try:
            # Attempt to click the 'go' button
            xpath_go = "//img[@class='go']"
            go_success = self.move_and_click(xpath_go, 10, True, "click the 'go' button", self.step, "clickable")
            if not go_success:
                raise TimeoutException("Failed to click the 'go' button.")
            
            # Attempt to click the 'check' button
            xpath_check = "//div[@class='theme-button']/p[text()='Check']"
            check_success = self.move_and_click(xpath_check, 10, True, "click the 'check' button", self.step, "clickable")
            if not check_success:
                raise TimeoutException("Failed to click the 'check' button.")

        except TimeoutException as e:
            if self.settings['debugIsOn']:
                self.output(f"Step {self.step} - {str(e)}", 3)

        finally:
            # Switch back to the original window, regardless of success or failure
            try:
                pass
                # self.driver.switch_to.window(original_window)
            except Exception as e:
                if self.settings['debugIsOn']:
                    self.output(f"Step {self.step} - Could not switch to the original window: {e}", 3)

        return go_success and check_success
  
    def get_balance(self, claimed=False):
        prefix = "After" if claimed else "Before"
        default_priority = 2 if claimed else 3

        priority = max(self.settings['verboseLevel'], default_priority)

        balance_text = f'{prefix} BALANCE:' if claimed else f'{prefix} BALANCE:'
        balance_xpath = f"//div[@class='balance']/p"

        try:
            element = self.monitor_element(balance_xpath, 15, "get balance")
            if element:
                balance_part = element
                self.output(f"Step {self.step} - {balance_text} {balance_part}", priority)

        except NoSuchElementException:
            self.output(f"Step {self.step} - Element containing '{prefix} Balance:' was not found.", priority)
        except Exception as e:
            self.output(f"Step {self.step} - An error occurred: {str(e)}", priority)

        self.increase_step()

    def get_wait_time(self, step_number="108", beforeAfter="pre-claim", max_attempts=1):
        for attempt in range(1, max_attempts + 1):
            try:
                self.output(f"Step {self.step} - Get the wait time...", 3)
                xpath = "//div[@class='mining']/p"
                elements = self.monitor_element(xpath, 10, "get claim timer")
                if elements:
                    return elements
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
        profit_xpath = "//p[text()='Mining Rate']/following-sibling::div[@class='mining-value']//span[last()]"

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

    def attempt_upgrade(self):
        pass

def main():
    claimer = TabizooClaimer()
    claimer.run()

if __name__ == "__main__":
    main()