"""Telegram login and two-factor authentication."""

import os
import shutil
import sys
import time
import re
import getpass
from PIL import Image
from pyzbar.pyzbar import decode
import qrcode_terminal
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys
from selenium.common.exceptions import NoSuchElementException, TimeoutException, StaleElementReferenceException


class TelegramMixin:
    """Telegram login and two-factor authentication. Uses the shared state on Claimer."""

    def log_into_telegram(self, user_input=None):

        self.step = "01"

        # Check and recreate directories
        self.session_path = f"./selenium/{user_input}"
        if os.path.exists(self.session_path):
            shutil.rmtree(self.session_path)
        os.makedirs(self.session_path, exist_ok=True)

        self.screenshots_path = f"./screenshots/{user_input}"
        if os.path.exists(self.screenshots_path):
            shutil.rmtree(self.screenshots_path)
        os.makedirs(self.screenshots_path, exist_ok=True)

        self.backup_path = f"./backups/{user_input}"
        if os.path.exists(self.backup_path):
            shutil.rmtree(self.backup_path)
        os.makedirs(self.backup_path, exist_ok=True)

        def visible_QR_code():
            max_attempts = 5
            attempt_count = 0
            last_url = "not a url"  # Placeholder for the last detected QR code URL

            xpath = "//canvas[@class='qr-canvas']"
            self.driver.get(self.url)
            wait = WebDriverWait(self.driver, 20)
            QR_code = wait.until(EC.visibility_of_element_located((By.XPATH, xpath)))
            wait = WebDriverWait(self.driver, 3)
            self.output(f"Step {self.step} - Waiting for the first QR code - may take up to 30 seconds.", 1)
            self.increase_step()

            while attempt_count < max_attempts:
                try:
                    # Attempt to find the QR code element
                    QR_code = wait.until(EC.visibility_of_element_located((By.XPATH, xpath)))
                    try:
                        # Attempt to take a screenshot of the QR code
                        QR_code.screenshot(f"{self.screenshots_path}/Step {self.step} - Initial QR code.png")
                    except StaleElementReferenceException:
                        self.output(f"Step {self.step} - QR code element is stale, refinding...", 1)
                        continue  # Retry by refinding the QR code element

                    image = Image.open(f"{self.screenshots_path}/Step {self.step} - Initial QR code.png")
                    decoded_objects = decode(image)
                    if decoded_objects:
                        this_url = decoded_objects[0].data.decode('utf-8')
                        if this_url != last_url:
                            last_url = this_url  # Update the last seen URL
                            attempt_count += 1
                            self.output("*** Important: Having GUI open in your Telegram App might stop this script from logging in! ***\n", 2)
                            self.output(f"Step {self.step} - Our screenshot path is {self.screenshots_path}\n", 1)
                            self.output(f"Step {self.step} - Generating screenshot {attempt_count} of {max_attempts}\n", 2)
                            qrcode_terminal.draw(this_url)
                        if attempt_count >= max_attempts:
                            self.output(f"Step {self.step} - Max attempts reached with no new QR code.", 1)
                            return False
                        time.sleep(0.5)  # Wait before the next check
                    else:
                        time.sleep(0.5)  # No QR code decoded, wait before retrying
                except (TimeoutException, NoSuchElementException):
                    self.output(f"Step {self.step} - QR Code is no longer visible.", 2)
                    return True  # Indicates the QR code has been scanned or disappeared

            self.output(f"Step {self.step} - Failed to generate a valid QR code after multiple attempts.", 1)
            return False  # If loop completes without a successful scan

        self.driver = self.get_driver()
    
        # QR Code Method
        if self.settings['screenshotQRCode']:
            try:
                while True:
                    if visible_QR_code():  # QR code not found
                        self.test_for_2fa()
                        return  # Exit the function entirely

                    # If we reach here, it means the QR code is still present:
                    choice = input(f"\nStep {self.step} - QR Code still present. Retry (r) with a new QR code or switch to the OTP method (enter): ")
                    print("")
                    if choice.lower() == 'r':
                        visible_QR_code()
                    else:
                        break

            except TimeoutException:
                self.output(f"Step {self.step} - Canvas not found: Restart the script and retry the QR Code or switch to the OTP method.", 1)

        # OTP Login Me,thod
        self.increase_step()
        self.output(f"Step {self.step} - Initiating the One-Time Password (OTP) method...\n",1)
        self.driver.get(self.url)
        xpath = "//button[contains(@class, 'btn-primary') and contains(., 'Log in by phone Number')]"
        self.move_and_click(xpath, 30, True, "switch to log in by phone number", self.step, "visible")
        self.increase_step()

        # Country Code Selection
        xpath = "//div[contains(@class, 'input-field-input')]"
        self.target_element = self.move_and_click(xpath, 30, True, "update user's country", self.step, "visible")
        if not self.target_element:
            self.output(f"Step {self.step} - Failed to find country input field.", 1)
            return

        user_input = input(f"Step {self.step} - Please enter your Country Name as it appears in the Telegram list: ").strip()
        self.target_element.send_keys(user_input)
        self.target_element.send_keys(Keys.RETURN)
        self.increase_step()

        # Phone Number Input
        xpath = "//div[contains(@class, 'input-field-input') and @inputmode='decimal']"
        self.target_element = self.move_and_click(xpath, 30, True, "request user's phone number", self.step, "visible")
        if not self.target_element:
            self.output(f"Step {self.step} - Failed to find phone number input field.", 1)
            return
    
        def validate_phone_number(phone):
            # Regex for validating an international phone number without leading 0 and typically 7 to 15 digits long
            pattern = re.compile(r"^[1-9][0-9]{6,14}$")
            return pattern.match(phone)

        while True:
            if self.settings['hideSensitiveInput']:
                user_phone = getpass.getpass(f"Step {self.step} - Please enter your phone number without leading 0 (hidden input): ")
            else:
                user_phone = input(f"Step {self.step} - Please enter your phone number without leading 0 (visible input): ")
    
            if validate_phone_number(user_phone):
                self.output(f"Step {self.step} - Valid phone number entered.",3)
                break
            else:
                self.output(f"Step {self.step} - Invalid phone number, must be 7 to 15 digits long and without leading 0.",1)
        self.target_element.send_keys(user_phone)
        self.increase_step()

        # Wait for the "Next" button to be clickable and click it    
        xpath = "//button//span[contains(text(), 'Next')]"
        self.move_and_click(xpath, 15, True, "click next to proceed to OTP entry", self.step, "visible")
        self.increase_step()

        try:
            # Attempt to locate and interact with the OTP field
            wait = WebDriverWait(self.driver, 20)
            if self.settings['debugIsOn']:
                self.debug_information("preparing for TG OTP","check")
            password = wait.until(EC.visibility_of_element_located((By.XPATH, "//input[@type='tel']")))
            otp = input(f"Step {self.step} - What is the Telegram OTP from your app? ")
            password.click()
            password.send_keys(otp)
            self.output(f"Step {self.step} - Let's try to log in using your Telegram OTP.\n",3)
            self.increase_step()

        except TimeoutException:
            # Check for Storage Offline
            xpath = "//button[contains(text(), 'STORAGE_OFFLINE')]"
            self.move_and_click(xpath, 10, True, "check for 'STORAGE_OFFLINE'", self.step, "visible")
            if self.target_element:
                self.output(f"Step {self.step} - ***Progress is blocked by a 'STORAGE_OFFLINE' button",1)
                self.output(f"Step {self.step} - If you are re-usi,ng an old Wallet session; try to delete or create a new session.",1)
                found_error = True
            # Check for flood wait
            xpath = "//button[contains(text(), 'FLOOD_WAIT')]"
            self.move_and_click(xpath, 10, True, "check for 'FLOOD_WAIT'", self.step, "visible")
            if self.target_element:
                self.output(f"Step {self.step} - ***Progress is blocked by a 'FLOOD_WAIT' button", 1)
                self.output(f"Step {self.step} - You need to wait for the specified number of seconds before retrying.", 1)
                self.output(f"Step {self.step} - {self.target_element.text}")
                found_error = True
            if not found_error:
                self.output(f"Step {self.step} - Selenium was unable to interact with the OTP screen for an unknown reason.")

        except Exception as e:  # Catch any other unexpected errors
            self.output(f"Step {self.step} - Login failed. Error: {e}", 1) 
            if self.settings['debugIsOn']:
                self.debug_information("telegram login failed","error")

        self.increase_step()
        self.test_for_2fa()

        if self.settings['debugIsOn']:
            self.debug_information("telegram OTP successfully entered","check")

    def test_for_2fa(self):
        try:
            self.increase_step()
            WebDriverWait(self.driver, 30).until(lambda d: d.execute_script('return document.readyState') == 'complete')
            xpath = "//input[@type='password' and contains(@class, 'input-field-input')]"
            fa_input = self.move_and_click(xpath, 15, False, "check for 2FA requirement (will timeout if you don't have 2FA)", self.step, "present")
        
            if fa_input:
                if self.settings['hideSensitiveInput']:
                    tg_password = getpass.getpass(f"Step {self.step} - Enter your Telegram 2FA password: ")
                else:
                    tg_password = input(f"Step {self.step} - Enter your Telegram 2FA password: ")
                fa_input.send_keys(tg_password + Keys.RETURN)
                self.output(f"Step {self.step} - 2FA password sent.\n", 3)
                self.output(f"Step {self.step} - Checking if the 2FA password is correct.\n", 2)
            
                xpath = "//*[contains(text(), 'Incorrect password')]"
                try:
                    incorrect_password = WebDriverWait(self.driver, 8).until(EC.visibility_of_element_located((By.XPATH, xpath)))
                    self.output(f"Step {self.step} - 2FA password is marked as incorrect by Telegram - check your debug screenshot if active.", 1)
                    if self.settings['debugIsOn']:
                        self.debug_information("incorrect telegram 2FA entered","error")
                    self.quit_driver()
                    sys.exit()  # Exit if incorrect password is detected
                except TimeoutException:
                    pass

                self.output(f"Step {self.step} - No password error found.", 3)
                xpath = "//input[@type='password' and contains(@class, 'input-field-input')]"
                fa_input = self.move_and_click(xpath, 5, False, "final check to make sure we are correctly logged in", self.step, "present")
                if fa_input:
                    self.output(f"Step {self.step} - 2FA password entry is still showing, check your debug screenshots for further information.\n", 1)
                    sys.exit()
                self.output(f"Step {self.step} - 2FA password check appears to have passed OK.\n", 3)
            else:
                self.output(f"Step {self.step} - 2FA input field not found.\n", 1)

        except TimeoutException:
            # 2FA field not found
            self.output(f"Step {self.step} - Two-factor Authorization not required.\n", 3)

        except Exception as e:  # Catch any other unexpected errors
            self.output(f"Step {self.step} - Login failed. 2FA Error - you'll probably need to restart the script: {e}", 1)
            if self.settings['debugIsOn']:
                self.debug_information("unspecified error during telegram 2FA","error")
