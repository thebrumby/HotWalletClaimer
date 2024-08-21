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

class PixelTapClaimer(Claimer):

    def initialize_settings(self):
        super().initialize_settings()
        self.script = "games/pixeltap.py"
        self.prefix = "PixelTap:"
        self.url = "https://web.telegram.org/k/#@pixelversexyzbot"
        self.pot_full = "FULL"
        self.pot_filling = "Mining"
        self.seed_phrase = None
        self.forceLocalProxy = False
        self.forceRequestUserAgent = False
        self.start_app_xpath = "//div[contains(@class, 'new-message-wrapper')]//div[contains(text(), 'Fight for supply')]"

    def __init__(self):
        self.settings_file = "variables.txt"
        self.status_file_path = "status.txt"
        self.wallet_id = ""
        self.load_settings()
        self.random_offset = random.randint(self.settings['lowestClaimOffset'], self.settings['highestClaimOffset'])
        super().__init__()

    def launch_iframe(self):
        super().launch_iframe()

        # Open tab in main window
        self.driver.switch_to.default_content()

        iframe = self.driver.find_element(By.TAG_NAME, "iframe")
        iframe_url = iframe.get_attribute("src")
        iframe_url = iframe_url.replace("tgWebAppPlatform=web", "tgWebAppPlatform=android")

        self.driver.execute_script("location.href = '" + iframe_url + "'")

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
            self.output(f"Step {self.step} - Failed to find or switch to the iframe within the timeout period.",1)

        except Exception as e:
            self.output(f"Step {self.step} - An error occurred: {e}",1)

    def full_claim(self):
        self.step = "100"
        self.launch_iframe()

        # Disable modals
        xpath = "(//div[contains(@class, 'MuiBackdrop-root')])[last()]"
        button = self.move_and_click(xpath, 10, False, "disable modals #1 (may not be present)", self.step, "clickable")
        if button: button.click()

        xpath = "(//div[contains(@class, 'MuiBackdrop-root')])[last()]"
        button = self.move_and_click(xpath, 5, False, "disable modals #2 (may not be present)", self.step, "clickable")
        if button: button.click()
            
        self.increase_step()

        self.get_balance(False)

        # CLAIM 
        xpath = "//button[contains(@class, 'claimButton')]"
        success = self.move_and_click(xpath, 8, True, "click the 'CLAIM' button", self.step, "clickable")
        # If the 'CLAIM' button click was successful, check for the presence of the specific div
        if success:
            status_text = "Main claim made."
        else:
            status_text = "Main claim not yet ready."
        self.increase_step()

        time.sleep(10)

        self.get_balance(True)

        wait_time = self.get_wait_time(self.step, "post-claim")

        # Select the 'Rewards' tab
        xpath = "//a[contains(span/text(), 'Rewards')]"
        success = self.move_and_click(xpath, 8, True, "click the 'Rewards TAB'", self.step, "clickable")
        self.increase_step()

        # If 'Rewards' tab selection was successful, proceed
        if success:
            # Open the 'CLAIM' pop-up
            xpath = "//button//span[contains(text(), 'Claim')]"
            success = self.move_and_click(xpath, 8, True, "open the 'CLAIM' pop-up", self.step, "clickable")
            self.increase_step()
    
            if success:
                # Click the 'CLAIM' button
                xpath = "//div[contains(text(), 'Claim') and not(contains(@class, 'disabled'))]"
                success = self.move_and_click(xpath, 8, True, "click the 'CLAIM' button", self.step, "clickable")
                self.increase_step()

                if success:
                    # Exit the 'CLAIM' pop-up
                    xpath = "//button[@class='closeBtn']"
                    success = self.move_and_click(xpath, 8, True, "exit the 'CLAIM' pop-up", self.step, "clickable")
                    self.increase_step()

                    if success:
                        status_text += " Daily reward claimed."
                    
                else:
                    status_text += " Daily reward not yet ready."


        if not status_text:
            status_text = "No reward or claim made on this occassion."

        self.output(f"STATUS: {status_text}",1)

        self.increase_step() 

        try:
            wait_time = int(wait_time)
            if wait_time < 60:
                wait_time = 60
        except (ValueError, TypeError):
             wait_time = 60
        # Now you can safely call random.randint
        random_value = random.randint(60, wait_time)
        return random_value


    def get_balance(self, claimed=False):

        prefix = "After" if claimed else "Before"
        default_priority = 2 if claimed else 3

        # Dynamically adjust the log priority
        priority = max(self.settings['verboseLevel'], default_priority)

        # Construct the specific balance XPath
        balance_text = f'{prefix} BALANCE:' if claimed else f'{prefix} BALANCE:'
        balance_xpath = "//div[@class='_balance_1erzm_18']/span[following-sibling::img]" 

        try:
            element = self.monitor_element(balance_xpath,15,"balance")
            cleaned_text = self.strip_html(element)
            # Check if element is not None and process the balance
            if element:
                self.output(f"Step {self.step} - {balance_text} {cleaned_text}", priority)

        except NoSuchElementException:
            self.output(f"Step {self.step} - Element containing '{prefix} Balance:' was not found.", priority)
        except Exception as e:
            self.output(f"Step {self.step} - An error occurred: {str(e)}", priority)  # Provide error as string for logging

        # Increment step function, assumed to handle next step logic
        self.increase_step()


    def get_wait_time(self, step_number="108", beforeAfter="pre-claim"):
        try:
            self.output(f"Step {self.step} - check if the timer is elapsing...", 3)
        
            xpath = "//div[contains(@class, 'claimTimer')]"
            wait_time_str = self.extract_time(self.strip_html_tags(self.monitor_element(xpath, 15, "claim timer")))

            if not wait_time_str:
                wait_time = 60
            else:
                wait_time = int(wait_time_str)

            self.output(f"Step {self.step} - The wait time is {wait_time} minutes.")

            return wait_time          
        except Exception as e:
            self.output(f"Step {self.step} - An error occurred: {e}", 3)
            if self.settings['debugIsOn']:
                screenshot_path = f"{self.screenshots_path}/{self.step}_get_wait_time_error.png"
                self.driver.save_screenshot(screenshot_path)
                self.output(f"Screenshot saved to {screenshot_path}", 3)
            return 60


    def extract_time(self, text):
        time_parts = text.split(':')
        if len(time_parts) == 3:
            try:
                hours = int(time_parts[0].strip())
                minutes = int(time_parts[1].strip())
                return hours * 60 + minutes
            except ValueError:
                return False
        return False
    
    def strip_html_tags(self, text):
        clean = re.compile('<.*?>')
        text_without_html = re.sub(clean, '', text)
        text_cleaned = re.sub(r'[^0-9:.]', '', text_without_html)
        return text_cleaned

def main():
    claimer = PixelTapClaimer()
    claimer.run()

if __name__ == "__main__":
    main()