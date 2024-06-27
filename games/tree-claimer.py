import os
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

class TreeClaimer(Claimer):

    def __init__(self):

        self.settings_file = "variables.txt"
        self.status_file_path = "status.txt"
        self.load_settings()
        self.random_offset = random.randint(self.settings['lowestClaimOffset'], self.settings['highestClaimOffset'])
        self.script = "games/tree.py"
        self.prefix = "TreeClaimer:"
        self.url = "https://www.treemine.app/login"
        self.pot_full = "0h 0m to fill"
        self.pot_filling = "to fill"

        super().__init__()

    def check_login(self):
        xpath = "//p[contains(text(), 'Seed phrase')]/ancestor-or-self::*/textarea"
        input_field = self.move_and_click(xpath, 5, True, "locate seedphrase textbox", self.step, "clickable")
        
        if input_field:
            seed_phrase = self.get_seed_phrase_from_file(self.screenshots_path)
            
            if not seed_phrase and int(self.step) < 100:
                seed_phrase = self.validate_seed_phrase()
                self.output("WARNING: Your seedphrase will be saved as an unencrypted file on your local filesystem if you choose 'y'!",1)
                save_to_file = input("Would you like to save the validated seed phrase to a text file? (y/N): ")
                if save_to_file.lower() == 'y':
                    seed_file_path = os.path.join(self.screenshots_path, 'seed.txt')
                    with open(seed_file_path, 'w') as file:
                        file.write(seed_phrase)
                    self.output(f"Seed phrase saved to {seed_file_path}", 3)
            if not seed_phrase and int(self.step) > 99:
                session = self.session_path.replace("./selenium/", "")
                self.output (f"Step {self.step} - You have become logged out: use './launch.sh tree {session} reset' from the Command Line to configure",1)
                while True:
                    input("Restart this PM2 once you have logged in again. Press Enter to continue...")

            input_field.send_keys(seed_phrase)
            self.output(f"Step {self.step} - Was successfully able to enter the seed phrase...", 3)
            self.increase_step()

            # Click the continue button after seed phrase entry:
            xpath = "//button[not(@disabled)]//span[contains(text(), 'Continue')]"
            self.move_and_click(xpath, 30, True, "click continue after seedphrase entry", self.step, "clickable")
            self.increase_step()
        else:
            self.output("Seed phrase textarea not found within the timeout period.", 2)
    
    def next_steps(self):
        self.driver = self.get_driver()
        self.driver.get("https://www.treemine.app/login")
        if self.step:
            pass
        else:
            self.step = "01"

        self.check_login()

        cookies_path = f"{self.session_path}/cookies.json"
        cookies = self.driver.get_cookies()
        with open(cookies_path, 'w') as file:
            json.dump(cookies, file)

    def find_working_link(self,old_step):
        self.output(f"Step {self.step} - Attempting to open a link Following Twitter...",2)

        start_app_xpath = "//p[contains(text(), 'RT')]"

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
                self.output(f"Step {self.step} - None of the 'Follow on Twitter' buttons were clickable.\n",1)
                if self.settings['debugIsOn']:
                    screenshot_path = f"{self.screenshots_path}/{self.step}-no-clickable-button.png"
                    self.driver.save_screenshot(screenshot_path)
                return False
            else:
                self.output(f"Step {self.step} - Successfully able to open a link to Follow on Twitter..\n",3)
                if self.settings['debugIsOn']:
                    screenshot_path = f"{self.screenshots_path}/{self.step}-app-opened.png"
                    self.driver.save_screenshot(screenshot_path)
                return True

        except TimeoutException:
            self.output(f"Step {self.step} - Failed to find the 'Follow on Twitter' button within the expected timeframe.\n",1)
            if self.settings['debugIsOn']:
                screenshot_path = f"{self.screenshots_path}/{self.step}-timeout-finding-button.png"
                self.driver.save_screenshot(screenshot_path)
            return False
        except Exception as e:
            self.output(f"Step {self.step} - An error occurred while trying to Follow on Twitter: {e}\n",1)
            if self.settings['debugIsOn']:
                screenshot_path = f"{self.screenshots_path}/{self.step}-unexpected-error-following-twitter.png"
                self.driver.save_screenshot(screenshot_path)
            return False

    def full_claim(self):
        self.driver = self.get_driver()
        
        self.step = "100"
        
        def get_seed_phrase(screenshots_path):
            seed_file_path = os.path.join(self.screenshots_path, 'seed.txt')
            if os.path.exists(seed_file_path):
                with open(seed_file_path, 'r') as file:
                    seed_phrase = file.read().strip()
                return seed_phrase
            else:
                return None

        def apply_random_offset(unmodifiedTimer):
            if self.settings['lowestClaimOffset'] <= self.settings['highestClaimOffset']:
                self.random_offset = random.randint(self.settings['lowestClaimOffset'], self.settings['highestClaimOffset'])
                modifiedTimer = unmodifiedTimer + self.random_offset
                self.output(f"Step {self.step} - Random offset applied to the wait timer of: {self.random_offset} minutes.", 2)
                return modifiedTimer
        
        self.driver.get("https://www.treemine.app/missions")
        
        self.check_login()
        self.increase_step()

        self.driver.get("https://www.treemine.app/missions")

        xpath = "//button[contains(text(), 'AXE')]"
        self.move_and_click(xpath, 30, True, "click the AXE button", self.step, "clickable")
        self.increase_step()

        def extract_minutes_from_string(text):
            match = re.search(r'(\d+)', text)
            if match:
                return int(match.group(1))
            return None

        xpath = "//span[contains(., 'minutes after')]"
        axe_time = self.move_and_click(xpath, 5, False, "check the axe time", self.step, "visible")
        if axe_time:
            minutes = extract_minutes_from_string(axe_time.text)
            if minutes is not None:
                self.output(f"Step {self.step} - The axe can not be claimed for another {minutes} minutes.", 2)
        else:
            self.find_working_link(self.step)
        self.increase_step()

        self.driver.get("https://www.treemine.app/miner")
        self.get_balance(False)
        self.increase_step()

        wait_time_text = self.get_wait_time(self.step, "pre-claim") 

        if wait_time_text != self.pot_full:
            matches = re.findall(r'(\d+)([hm])', wait_time_text)
            remaining_wait_time = (sum(int(value) * (60 if unit == 'h' else 1) for value, unit in matches)) + self.random_offset
            if remaining_wait_time < 5 or self.settings["forceClaim"]:
                self.settings['forceClaim'] = True
                self.output(f"Step {self.step} - the remaining time to claim is less than the random offset, so applying: settings['forceClaim'] = True", 3)
            else:
                if remaining_wait_time > 90:
                    self.output(f"Step {self.step} - Initial wait time returned as {remaining_wait_time}.",3)
                    self.increase_step()
                    remaining_wait_time = 90
                    self.random_offset = 0
                    wait_time_text = "1h30m"
                    self.output(f"Step {self.step} - As there are no gas fees with Tree coin - claim forced to 90 minutes.",3)
                    self.increase_step()
                self.output(f"STATUS: Considering {wait_time_text}, we'll go back to sleep for {remaining_wait_time} minutes.", 1)
                return remaining_wait_time

        if wait_time_text == "Unknown":
            return 15

        try:
            self.output(f"Step {self.step} - The pre-claim wait time is : {wait_time_text} and random offset is {self.random_offset} minutes.",1)
            self.increase_step()

            if wait_time_text == self.pot_full or self.settings['forceClaim']:
                try:
                    original_window = self.driver.current_window_handle
                    xpath = "//button[contains(text(), 'Check NEWS')]"
                    self.move_and_click(xpath, 3, True, "check for NEWS.", self.step, "clickable")
                    self.driver.switch_to.window(original_window)
                except TimeoutException:
                    if self.settings['debugIsOn']:
                        self.output(f"Step {self.step} - No news to check or button not found.",3)
                self.increase_step()

                try:
                    # Click on the "Claim HOT" button:
                    xpath = "//button[contains(text(), 'Claim')]"
                    self.move_and_click(xpath, 30, True, "click the claim button", self.step, "clickable")
                    self.increase_step()

                    # Now let's try again to get the time remaining until filled. 
                    # 4th April 24 - Let's wait for the spinner to disappear before trying to get the new time to fill.
                    self.output(f"Step {self.step} - Let's wait for the pending Claim spinner to stop spinning...",2)
                    time.sleep(5)
                    wait = WebDriverWait(self.driver, 240)
                    spinner_xpath = "//*[contains(@class, 'spinner')]" 
                    try:
                        wait.until(EC.invisibility_of_element_located((By.XPATH, spinner_xpath)))
                        self.output(f"Step {self.step} - Pending action spinner has stopped.\n",3)
                    except TimeoutException:
                        self.output(f"Step {self.step} - Looks like the site has lag - the Spinner did not disappear in time.\n",2)
                    self.increase_step()
                    wait_time_text = self.get_wait_time(self.step, "post-claim") 
                    matches = re.findall(r'(\d+)([hm])', wait_time_text)
                    total_wait_time = apply_random_offset(sum(int(value) * (60 if unit == 'h' else 1) for value, unit in matches))
                    self.increase_step()

                    if total_wait_time > 90:
                        total_wait_time = 90
                        self.output(f"Step {self.step} - As there are no gas fees with Tree coin - claim forced to 90 minutes.",2)
                        self.increase_step()

                    self.get_balance(True)

                    if wait_time_text == "Filled":
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
        global step
        prefix = "After" if claimed else "Before"
        default_priority = 2 if claimed else 3

        # Dynamically adjust the log priority
        priority = max(self.settings['verboseLevel'], default_priority)

        # Construct the specific balance XPath
        balance_text = f'{prefix} BALANCE:' if claimed else f'{prefix} BALANCE:'
        balance_xpath = f"//span[contains(text(), 'TREE Balance:')]/following-sibling::span[1]"

        try:
            # Wait for the element to be visible based on the XPath
            element = WebDriverWait(self.driver, 10).until(
                EC.visibility_of_element_located((By.XPATH, balance_xpath))
            )

            # Check if element is not None and process the balance
            if element:
                balance_part = element.text.strip()
                self.output(f"Step {step} - {balance_text} {balance_part}", priority)

        except NoSuchElementException:
            self.output(f"Step {step} - Element containing '{prefix} Balance:' was not found.", priority)
        except Exception as e:
            self.output(f"Step {step} - An error occurred: {str(e)}", priority)  # Provide error as string for logging

        # Increment step function, assumed to handle next step logic
        self.increase_step()

    def get_wait_time(self, step_number="108", beforeAfter = "pre-claim", max_attempts=2):
    
        for attempt in range(1, max_attempts + 1):
            try:
                xpath = f"//div[contains(., 'Storage')]//p[contains(., '{self.pot_full}') or contains(., '{self.pot_filling}')]"
                wait_time_element = self.move_and_click(xpath, 20, True, f"get the {beforeAfter} wait timer", self.step, "visible")
                # Check if wait_time_element is not None
                if wait_time_element is not None:
                    return wait_time_element.text
                else:
                    self.output(f"Step {step} - Attempt {attempt}: Wait time element not found. Clicking the 'Storage' link and retrying...",3)
                    storage_xpath = "//h4[text()='Storage']"
                    self.move_and_click(storage_xpath, 30, True, "click the 'storage' link", f"{self.step} recheck", "clickable")
                    self.output(f"Step {self.step} - Attempted to select strorage again...",3)
                return wait_time_element.text

            except TimeoutException:
                if attempt < max_attempts:  # Attempt failed, but retries remain
                    self.output(f"Step {self.step} - Attempt {attempt}: Wait time element not found. Clicking the 'Storage' link and retrying...",3)
                    storage_xpath = "//h4[text()='Storage']"
                    self.move_and_click(storage_xpath, 30, True, "click the 'storage' link", f"{self.step} recheck", "clickable")
                else:  # No retries left after initial failure
                    self.output(f"Step {step} - Attempt {attempt}: Wait time element not found.",3)

            except Exception as e:
                self.output(f"Step {step} - An error occurred on attempt {attempt}: {e}",3)

        # If all attempts fail         
        return "Unknown"


def main():
    claimer = TreeClaimer()
    claimer.run()


if __name__ == "__main__":
    main()
