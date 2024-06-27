import time
import re
import json
import random
from selenium.webdriver import ActionChains
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import NoSuchElementException, TimeoutException, StaleElementReferenceException, ElementClickInterceptedException

from claimer import Claimer

class DiamondClaimer(Claimer):

    def __init__(self):

        self.settings_file = "variables.txt"
        self.status_file_path = "status.txt"
        self.load_settings()
        self.random_offset = random.randint(self.settings['lowestClaimOffset'], self.settings['highestClaimOffset'])
        self.script = "games/diamond.py"
        self.prefix = "DiamondClaimer:"
        self.url = "https://web.telegram.org/k/#@holdwallet_bot"
        self.pot_full = "Filled"
        self.pot_filling = "to fill"
        self.seed_phrase = None

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
            # Let's click the login button first:
            xpath = "//a[contains(text(), 'Login')]"
            self.target_element = self.move_and_click(xpath, 30, False, "find the HoldWallet log-in button", "08", "visible")
            self.driver.execute_script("arguments[0].click();", self.target_element)
            self.increase_step()

            # Then look for the seed phase textarea:
            xpath = "//div[@class='form-input'][label[text()='Seed or private key']]/textarea"
            input_field = self.move_and_click(xpath, 30, True, "locate seedphrase textbox", self.step, "clickable")
            if not self.imported_seedphrase:
                self.imported_seedphrase = self.validate_seed_phrase()
            input_field.send_keys(self.imported_seedphrase) 
            self.output(f"Step {self.step} - Was successfully able to enter the seed phrase...",3)
            self.increase_step()

            # Click the continue button after seed phrase entry:
            xpath = "//button[contains(text(), 'Continue')]"
            self.move_and_click(xpath, 30, True, "click continue after seedphrase entry", self.step, "clickable")
            self.increase_step()

            # Click the account selection button:
            xpath = "//div[contains(text(), 'Select account')]"
            self.move_and_click(xpath, 20, True, "click account selection (may not be present)", self.step, "clickable")
            self.increase_step()

            cookies_path = f"{self.session_path}/cookies.json"
            cookies = self.driver.get_cookies()
            with open(cookies_path, 'w') as file:
                json.dump(cookies, file)

        except TimeoutException:
            self.output(f"Step {self.step} - Failed to find or switch to the iframe within the timeout period.",1)

        except Exception as e:
            self.output(f"Step {self.step} - An error occurred: {e}",1)

    def launch_iframe(self):
        self.driver = self.get_driver()

        try:
            self.driver.get(self.url)
            WebDriverWait(self.driver, 30).until(lambda d: d.execute_script('return document.readyState') == 'complete')
            self.output(f"Step {self.step} - Attempting to verify if we are logged in (hopefully QR code is not present).",3)
            xpath = "//canvas[@class='qr-canvas']"
            wait = WebDriverWait(self.driver, 5)
            wait.until(EC.visibility_of_element_located((By.XPATH, xpath)))
            if self.settings['debugIsOn']:
                screenshot_path = f"{self.screenshots_path}/Step {self.step} - Test QR code after session is resumed.png"
                self.driver.save_screenshot(screenshot_path)
            self.output(f"Step {self.step} - Chrome driver reports the QR code is visible: It appears we are no longer logged in.",2)
            self.output(f"Step {self.step} - Most likely you will get a warning that the central input box is not found.",2)
            self.output(f"Step {self.step} - System will try to restore session, or restart the script from CLI force a fresh log in.\n",2)

        except TimeoutException:
            self.output(f"Step {self.step} - nothing found to action. The QR code test passed.\n",3)
        self.increase_step()

        self.driver.get(self.url)
        WebDriverWait(self.driver, 30).until(lambda d: d.execute_script('return document.readyState') == 'complete')

        # There is a very unlikely scenario that the chat might have been cleared.
        # In this case, the "START" button needs pressing to expose the chat window!
        xpath = "//button[contains(., 'START')]"
        button = self.move_and_click(xpath, 3, False, "check for the start button (should not be present)", self.step, "clickable")
        if button:
            button.click()
        self.increase_step()


        # New link logic to avoid finding and expired link
        if self.find_working_link(self.step):
            self.increase_step()
        else:
            self.send_start(self.step)
            self.increase_step()
            self.find_working_link(self.step)
            self.increase_step()

        # Now let's move to and JS click the "Launch" Button
        xpath = "//button[contains(@class, 'popup-button') and contains(., 'Launch')]"
        button = self.move_and_click(xpath, 8, False, "click the 'Launch' button", self.step, "clickable")
        if button:
            button.click()
        self.increase_step()

        # HereWalletBot Pop-up Handling
        self.select_iframe(self.step)
        self.increase_step()

    def full_claim(self):
        self.step = "100"

        def apply_random_offset(unmodifiedTimer):
            if self.settings['lowestClaimOffset'] <= self.settings['highestClaimOffset']:
                self.random_offset = random.randint(self.settings['lowestClaimOffset'], self.settings['highestClaimOffset'])
                modifiedTimer = unmodifiedTimer + self.random_offset
                self.output(f"Step {self.step} - Random offset applied to the wait timer of: {self.random_offset} minutes.", 2)
                return modifiedTimer

        self.launch_iframe()

        # Click on the Storage link:
        xpath = "//h2[text()='Mining']"
        self.move_and_click(xpath, 30, True, "click the 'storage' link", self.step, "clickable")
        self.increase_step

        self.get_balance(False)

        wait_time_text = self.get_wait_time(self.step, "pre-claim") 

        if wait_time_text != "0h 0m to fill":
            matches = re.findall(r'(\d+)([hm])', wait_time_text)
            remaining_wait_time = (sum(int(value) * (60 if unit == 'h' else 1) for value, unit in matches)) + self.random_offset
            if remaining_wait_time < 5 or self.settings["forceClaim"]:
                self.settings['forceClaim'] = True
                self.output(f"Step {self.step} - the remaining time to claim is less than the random offset, so applying: settings['forceClaim'] = True", 3)
            else:
                self.output(f"STATUS: Considering {wait_time_text}, we'll go back to sleep for {remaining_wait_time} minutes.", 1)
                return remaining_wait_time

        if wait_time_text == "Unknown":
            return 15

        try:
            self.output(f"Step {self.step} - The pre-claim wait time is : {wait_time_text} and random offset is {self.random_offset} minutes.",1)
            self.increase_step()

            if wait_time_text == "0h 0m to fill" or self.settings['forceClaim']:
                try:         
                    # Click on the "Claim" button:
                    xpath = "//button[contains(text(), 'Claim')]"
                    self.move_and_click(xpath, 30, True, "click the claim button", self.step, "clickable")
                    self.increase_step()

                    # Now let's try again to get the time remaining until filled. 
                    # 4th April 24 - Let's wait for the spinner to disappear before trying to get the new time to fill.
                    self.output(f"Step {self.step} - Let's wait for the pending Claim spinner to stop spinning...",2)
                    time.sleep(5)
                    wait_time_text = self.get_wait_time(self.step, "post-claim") 
                    matches = re.findall(r'(\d+)([hm])', wait_time_text)
                    total_wait_time = apply_random_offset(sum(int(value) * (60 if unit == 'h' else 1) for value, unit in matches))
                    self.increase_step()

                    self.get_balance(True)

                    if wait_time_text == "0h 0m to fill":
                        self.output(f"STATUS: The wait timer is still showing: Filled.",1)
                        self.output(f"Step {self.step} - This means either the claim failed, or there is >4 minutes lag in the game.",1)
                        self.output(f"Step {self.step} - We'll check back in 1 hour to see if the claim processed and if not try again.",2)
                    else:
                        self.output(f"STATUS: Successful Claim: Next claim {wait_time_text} / {total_wait_time} minutes.",1)
                    return max(60, total_wait_time)

                except TimeoutException:
                    self.output(f"STATUS: The claim process timed out: Maybe the site has lag? Will retry after one hour.",1)
                    return 60
                except Exception as e:
                    self.output(f"STATUS: An error occurred while trying to claim: {e}\nLet's wait an hour and try again",1)
                    return 60

            else:
                # If the wallet isn't ready to be claimed, calculate wait time based on the timer provided on the page
                matches = re.findall(r'(\d+)([hm])', wait_time_text)
                if matches:
                    total_time = sum(int(value) * (60 if unit == 'h' else 1) for value, unit in matches)
                    total_time += 1
                    total_time = max(5, total_time) # Wait at least 5 minutes or the time
                    self.output(f"Step {self.step} - Not Time to claim this wallet yet. Wait for {total_time} minutes until the storage is filled.",2)
                    return total_time 
                else:
                    self.output(f"Step {self.step} - No wait time data found? Let's check again in one hour.",2)
                    return 60  # Default wait time when no specific time until filled is found.
        except Exception as e:
            self.output(f"Step {self.step} - An unexpected error occurred: {e}",1)
            return 60  # Default wait time in case of an unexpected error
        
    def get_balance(self, claimed=False):

        def strip_html_and_non_numeric(text):
            """Remove HTML tags and keep only numeric characters and decimal points."""
            # Remove HTML tags
            clean = re.compile('<.*?>')
            text_without_html = clean.sub('', text)
            # Keep only numeric characters and decimal points
            numeric_text = re.sub(r'[^0-9.]', '', text_without_html)
            return numeric_text

        prefix = "After" if claimed else "Before"
        default_priority = 2 if claimed else 3

        # Dynamically adjust the log priority
        priority = max(self.settings['verboseLevel'], default_priority)

        # Construct the specific balance XPath
        balance_text = f'{prefix} BALANCE:' if claimed else f'{prefix} BALANCE:'
        balance_xpath = f"//small[text()='DMH Balance']/following-sibling::div"

        try:
            element = strip_html_and_non_numeric(self.monitor_element(balance_xpath))

            # Check if element is not None and process the balance
            if element:
                self.output(f"Step {self.step} - {balance_text} {element}", priority)

        except NoSuchElementException:
            self.output(f"Step {self.step} - Element containing '{prefix} Balance:' was not found.", priority)
        except Exception as e:
            self.output(f"Step {self.step} - An error occurred: {str(e)}", priority)  # Provide error as string for logging

        # Increment step function, assumed to handle next step logic
        self.increase_step()

    def get_wait_time(self, step_number="108", beforeAfter="pre-claim"):
        try:
            xpath = "//div[div[p[text()='Storage']]]//span[contains(text(), 'to fill') or contains(text(), 'Filled')]"
            wait_time_element = self.move_and_click(xpath, 20, True, f"get the {beforeAfter} wait timer", step_number, "visible")
            # Check if wait_time_element is not None
            if wait_time_element is not None:
                return wait_time_element.text
            else:
                return "Unknown"
        except Exception as e:
            self.output(f"Step {step_number} - An error occurred: {e}", 3)
            return "Unknown"

    def find_working_link(self, old_step):
        self.output(f"Step {self.step} - Attempting to open a link for the app...",2)

        start_app_xpath = "//div[text()='Open Wallet']"
        try:
            start_app_buttons = WebDriverWait(self.driver, 5).until(EC.presence_of_all_elements_located((By.XPATH, start_app_xpath)))
            clicked = False

            for button in reversed(start_app_buttons):
                actions = ActionChains(self.driver)
                actions.move_to_element(button).pause(0.2)
                try:
                    if self.settings['debugIsOn']:
                        self.driver.save_screenshot(f"{self.screenshots_path}/{self.step} - Find working link.png".format(self.screenshots_path))
                    actions.perform()
                    self.driver.execute_script("arguments[0].click();", button)
                    clicked = True
                    break
                except StaleElementReferenceException:
                    continue
                except ElementClickInterceptedException:
                    continue

            if not clicked:
                self.output(f"Step {self.step} - None of the 'Open Wallet' buttons were clickable.\n",1)
                if self.settings['debugIsOn']:
                    screenshot_path = f"{self.screenshots_path}/{self.step}-no-clickable-button.png"
                    self.driver.save_screenshot(screenshot_path)
                return False
            else:
                self.output(f"Step {self.step} - Successfully able to open a link for the app..\n",3)
                if self.settings['debugIsOn']:
                    screenshot_path = f"{self.screenshots_path}/{self.step}-app-opened.png"
                    self.driver.save_screenshot(screenshot_path)
                return True

        except TimeoutException:
            self.output(f"Step {self.step} - Failed to find the 'Open Wallet' button within the expected timeframe.\n",1)
            if self.settings['debugIsOn']:
                screenshot_path = f"{self.screenshots_path}/{self.step}-timeout-finding-button.png"
                self.driver.save_screenshot(screenshot_path)
            return False
        except Exception as e:
            self.output(f"Step {self.step} - An error occurred while trying to open the app: {e}\n",1)
            if self.settings['debugIsOn']:
                screenshot_path = f"{self.screenshots_path}/{self.step}-unexpected-error-opening-app.png"
                self.driver.save_screenshot(screenshot_path)
            return False


def main():
    claimer = DiamondClaimer()
    claimer.run()

if __name__ == "__main__":
    main()