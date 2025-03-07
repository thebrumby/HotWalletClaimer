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

class WaveClaimer(Claimer):

    def initialize_settings(self):
        super().initialize_settings()
        self.script = "games/wave.py"
        self.prefix = "Wave:"
        self.url = "https://web.telegram.org/k/#@waveonsuibot"
        self.pot_full = "Filled"
        self.pot_filling = "to fill"
        self.seed_phrase = None
        self.forceLocalProxy = False
        self.forceRequestUserAgent = False
        self.start_app_xpath = "//span[contains(text(), 'Log in to Wave') or contains(text(), 'Open Wave App')]"

    def __init__(self):
        self.settings_file = "variables.txt"
        self.status_file_path = "status.txt"
        self.wallet_id = ""
        self.load_settings()
        self.random_offset = random.randint(self.settings['lowestClaimOffset'], self.settings['highestClaimOffset']) + 1
        super().__init__()
        
    def switch_tab(self):
        """ List all open tabs, log them, and switch to the newest one. """
        tabs = self.driver.window_handles
        self.output(f"Step {self.step} - Found {len(tabs)} open tab(s):", 3)
        
        # Log each tab's URL
        for index, tab in enumerate(tabs):
            self.driver.switch_to.window(tab)
            self.output(f"→ Tab {index + 1}: {self.driver.current_url}", 3)
        
        # ✅ Switch to the newest tab
        if len(tabs) > 1:
            self.driver.switch_to.window(tabs[-1])
            self.output(f"Step {self.step} - Switched to the new tab: {self.driver.current_url}", 3)
        else:
            self.output(f"Step {self.step} - No new tab detected, staying on the current page.", 3)

    def next_steps(self):
        if not self.step:
            self.step = "01"
    
        def switch_tab():
            """ List all open tabs, log them, and switch to the newest one. """
            tabs = self.driver.window_handles
            self.output(f"Step {self.step} - Found {len(tabs)} open tab(s):", 3)
        
            # Log each tab's URL
            for index, tab in enumerate(tabs):
                self.driver.switch_to.window(tab)
                self.output(f"→ Tab {index + 1}: {self.driver.current_url}", 3)
        
            # ✅ Switch to the newest tab
            if len(tabs) > 1:
                self.driver.switch_to.window(tabs[-1])
                self.output(f"Step {self.step} - Switched to the new tab: {self.driver.current_url}", 3)
            else:
                self.output(f"Step {self.step} - No new tab detected, staying on the current page.", 3)

        def validate_telegram():
            """ Validate Telegram login sequence. """
            self.switch_tab()
    
            xpath = "//span[contains(text(), 'Open in Web')]"
            self.move_and_click(xpath, 30, True, "check for the Open pop-up", self.step, "clickable")
            self.increase_step() 
    
            xpath = "(//span[contains(text(), 'Log in to Wave')])[last()]"
            self.move_and_click(xpath, 10, True, "find the last game link for the access token", self.step, "clickable")
            self.increase_step()
            
            xpath = "//button[contains(@class, 'popup-button') and contains(., 'Open')]"
            self.move_and_click(xpath, 10, True, "check for the 'Open' pop-up (may not be present)", self.step, "clickable")
            self.increase_step()
    
            self.switch_tab()
            
            # Step 3: Import Wallet (only if needed)
            xpath = "//button[normalize-space(text())='Import Wallet']"
            if self.move_and_click(xpath, 10, True, "import seed phrase (may not be present)", self.step, "clickable"):
                populate_seedphrase()
            self.increase_step()
    
        def populate_seedphrase():
            """ Populate the seed phrase if required. """
            try:
                # Step 1: Enter Seed Phrase
                xpath = "//p[contains(text(), 'Seed phrase or Private key')]/following-sibling::textarea[1]"
                input_field = WebDriverWait(self.driver, 30).until(
                    EC.visibility_of_element_located((By.XPATH, xpath))
                )
    
                self.driver.execute_script("arguments[0].click();", input_field)
                input_field.send_keys(self.validate_seed_phrase())
                self.output(f"Step {self.step} - Successfully entered the seed phrase...", 3)
    
            except Exception as e:
                self.output(f"Step {self.step} - Failed to enter the seed phrase: {str(e)}", 2)
    
            self.increase_step()  # Always increase step, even if input fails
    
            # Step 2: Click Continue after entering the seed phrase
            xpath = "//button[normalize-space(text())='Continue']"
            self.move_and_click(xpath, 10, True, "click continue after seed phrase entry", self.step, "clickable")
            self.increase_step()
    
        try:
            # Step 1: Log in to Wave
            xpath = "//span[contains(text(), 'Log in to Wave') or contains(text(), 'Open Wave App')]"
            self.find_working_link(self.step, xpath)
            self.increase_step()
            
            xpath = "//button[contains(@class, 'popup-button') and contains(., 'Open')]"
            self.move_and_click(xpath, 10, True, "check for the 'Open' pop-up (may not be present)", self.step, "clickable")
            self.increase_step()
            
            self.switch_tab()
    
            # Step 2: Validate Telegram session if it's not already done
            xpath = "//span[normalize-space(text())='Login Telegram']"
            if self.move_and_click(xpath, 10, True, "initiate the 'Log In' link (may not be present)", self.step, "clickable"):
                validate_telegram()
            self.increase_step()
    
            # Step 3: Check we're logged in
            xpath = "//span[contains(text(), 'Ocean Game')]"
            if self.move_and_click(xpath, 10, True, "click the 'Claim Now' link", self.step, "visible"):
                self.output(f"Step {self.step} - We appear to have successfully logged in", 2)
                self.set_cookies()  # ✅ Only set cookies if login was successful
            else:
                self.output(f"STATUS We appear to have failed to log in!", 1)
            self.increase_step()
    
        except TimeoutException:
            self.output(f"Step {self.step} - Failed to find or switch to the iframe within the timeout period.", 1)
    
        except Exception as e:
            self.output(f"Step {self.step} - An error occurred: {e}", 1)
            
    def launch_iframe(self):
        self.driver = self.get_driver()
        # Set viewport size for a desktop browser, e.g. 1920x1080 for a full HD experience
        self.driver.set_window_size(1920, 1080)

        # let's start with clean screenshots directory
        if int(self.step) < 101:
            if os.path.exists(self.screenshots_path):
                shutil.rmtree(self.screenshots_path)
            os.makedirs(self.screenshots_path)

        try:
            self.driver.get(self.url)
            WebDriverWait(self.driver, 30).until(lambda d: d.execute_script('return document.readyState') == 'complete')
            self.output(f"Step {self.step} - Attempting to verify if we are logged in (hopefully QR code is not present).", 2)
            xpath = "//canvas[@class='qr-canvas']"
            if self.settings['debugIsOn']:
                self.debug_information("QR code check during session start","check")
            wait = WebDriverWait(self.driver, 10)
            wait.until(EC.visibility_of_element_located((By.XPATH, xpath)))
            self.output(f"Step {self.step} - Chrome driver reports the QR code is visible: It appears we are no longer logged in.", 2)
            self.output(f"Step {self.step} - Most likely you will get a warning that the central input box is not found.", 2)
            self.output(f"Step {self.step} - System will try to restore session, or restart the script from CLI to force a fresh log in.\n", 2)

        except TimeoutException:
            self.output(f"Step {self.step} - nothing found to action. The QR code test passed.\n", 3)
        self.increase_step()

        self.driver.get(self.url)
        WebDriverWait(self.driver, 30).until(lambda d: d.execute_script('return document.readyState') == 'complete')
        
        for _ in range(3):
            self.output(f"Step {self.step} - Loading: {str(self.url)}", 3)
            self.driver.get(self.url)
            WebDriverWait(self.driver, 30).until(lambda d: d.execute_script('return document.readyState') == 'complete')
            title_xapth = "(//div[@class='user-title']//span[contains(@class, 'peer-title')])[1]"
            try:
                wait = WebDriverWait(self.driver, 30)
                wait.until(EC.visibility_of_element_located((By.XPATH, title_xapth)))
                title = self.monitor_element(title_xapth, 10, "Get current page title")
                self.output(f"Step {self.step} - The current page title is: {title}", 3)
                break
            except TimeoutException:
                self.output(f"Step {self.step} - not found title.", 3)
                if self.settings['debugIsOn']:
                    self.debug_information("App title check during telegram load", "check")
                time.sleep(5)

        # There is a very unlikely scenario that the chat might have been cleared.
        # In this case, the "START" button needs pressing to expose the chat window!
        xpath = "//button[contains(., 'START')]"
        button = self.move_and_click(xpath, 8, True, "check for the start button (should not be present)", self.step, "clickable")
        self.increase_step()

        # HereWalletBot Pop-up Handling
        self.output(f"Step {self.step} - Preparatory steps complete, handing over to the main setup/claim function...", 2)


    def full_claim(self):
        self.step = "100"

        def apply_random_offset(unmodifiedTimer):
            lowest_claim_offset = max(0, self.settings['lowestClaimOffset'])
            highest_claim_offset = max(0, self.settings['highestClaimOffset'])
            if self.settings['lowestClaimOffset'] <= self.settings['highestClaimOffset']:
                self.random_offset = random.randint(lowest_claim_offset, highest_claim_offset) + 1
                modifiedTimer = unmodifiedTimer + self.random_offset
                self.output(f"Step {self.step} - Random offset applied to the wait timer of: {self.random_offset} minutes.", 2)
                return modifiedTimer

        self.launch_iframe()
        
        xpath = "(//span[contains(text(), 'Log in to Wave')])[last()]"
        self.move_and_click(xpath, 10, True, "find the last game link for the access token", self.step, "clickable")
        self.increase_step()
            
        xpath = "//button[contains(@class, 'popup-button') and contains(., 'Open')]"
        self.move_and_click(xpath, 10, True, "check for the 'Open' pop-up (may not be present)", self.step, "clickable")
        self.increase_step()
        
        self.switch_tab()

        xpath = "//button//span[contains(text(), 'Claim Now')]"
        button = self.move_and_click(xpath, 10, False, "click the 'Ocean Game' link", self.step, "visible")
        self.driver.execute_script("arguments[0].click();", button)
        self.increase_step()

        self.get_balance(False)
        self.get_profit_hour(False)

        wait_time_text = self.get_wait_time(self.step, "pre-claim")

        if wait_time_text != self.pot_full:
            matches = re.findall(r'(\d+)([hm])', wait_time_text)
            remaining_wait_time = (sum(int(value) * (60 if unit == 'h' else 1) for value, unit in matches))
            if remaining_wait_time < 5 or self.settings["forceClaim"]:
                self.settings['forceClaim'] = True
                self.output(f"Step {self.step} - the remaining time to claim is short so let's claim anyway, so applying: settings['forceClaim'] = True", 3)
            else:
                remaining_wait_time += self.random_offset
                self.output(f"STATUS: Considering {wait_time_text}, we'll go back to sleep for {remaining_wait_time} minutes.", 1)
                return remaining_wait_time

        if not wait_time_text:
            return 60

        try:
            self.output(f"Step {self.step} - The pre-claim wait time is : {wait_time_text} and random offset is {self.random_offset} minutes.", 1)
            self.increase_step()

            if wait_time_text == self.pot_full or self.settings['forceClaim']:
                try:
                    xpath = "//div[contains(text(), 'Claim Now')]"
                    button = self.move_and_click(xpath, 10, False, "click the claim button", self.step, "present")
                    try:
                        self.driver.execute_script("arguments[0].click();", button)
                        self.increase_step()
                    except Exception:
                        pass

                    self.output(f"Step {self.step} - Let's wait for the pending Claim spinner to stop spinning...", 2)
                    time.sleep(5)
                    wait = WebDriverWait(self.driver, 240)
                    spinner_xpath = "//*[contains(@class, 'spinner')]"
                    try:
                        wait.until(EC.invisibility_of_element_located((By.XPATH, spinner_xpath)))
                        self.output(f"Step {self.step} - Pending action spinner has stopped.\n", 3)
                    except TimeoutException:
                        self.output(f"Step {self.step} - Looks like the site has lag - the Spinner did not disappear in time.\n", 2)
                    self.increase_step()
                    wait_time_text = self.get_wait_time(self.step, "post-claim")
                    matches = re.findall(r'(\d+)([hm])', wait_time_text)
                    total_wait_time = apply_random_offset(sum(int(value) * (60 if unit == 'h' else 1) for value, unit in matches))
                    self.increase_step()

                    self.get_balance(True)

                    if wait_time_text == self.pot_full:
                        self.output(f"STATUS: The wait timer is still showing: Filled.", 1)
                        self.output(f"Step {self.step} - This means either the claim failed, or there is >4 minutes lag in the game.", 1)
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
        
    def get_balance(self, claimed=False):
        prefix = "After" if claimed else "Before"
        default_priority = 2 if claimed else 3

        priority = max(self.settings['verboseLevel'], default_priority)

        balance_text = f'{prefix} BALANCE:' if claimed else f'{prefix} BALANCE:'
        xpath = "//p[contains(@class, 'wave-balance')]"

        try:
            element = WebDriverWait(self.driver, 20).until(
                EC.presence_of_element_located((By.XPATH, xpath))
            )

            balance_part = self.driver.execute_script("return arguments[0].textContent.trim();", element)
            
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
                xpath = "//span[contains(@class, 'boat_balance')]"
                wait_time_element = self.move_and_click(xpath, 5, True, f"get the {beforeAfter} wait timer (time elapsing method)", self.step, "present")
                if wait_time_element is not None:
                    return wait_time_element.text
                xpath = "//div[contains(text(), 'Claim Now')]"
                wait_time_element = self.move_and_click(xpath, 10, False, f"get the {beforeAfter} wait timer (pot full method)", self.step, "present")
                if wait_time_element is not None:
                    return self.pot_full
                    
            except Exception as e:
                self.output(f"Step {self.step} - An error occurred on attempt {attempt}: {e}", 3)

        return False

    def get_profit_hour(self, claimed=False):
        prefix = "After" if claimed else "Before"
        default_priority = 2 if claimed else 3

        priority = max(self.settings['verboseLevel'], default_priority)

        # Construct the specific profit XPath
        profit_text = f'{prefix} PROFIT/HOUR:'
        profit_xpath = "//span[text()='Aqua Cat']/following-sibling::span[1]"

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

def main():
    claimer = WaveClaimer()
    claimer.run()

if __name__ == "__main__":
    main()
