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

class OxygenAUClaimer(Claimer):

    def __init__(self):
        self.settings_file = "variables.txt"
        self.status_file_path = "status.txt"
        self.load_settings()
        self.random_offset = random.randint(self.settings['lowestClaimOffset'], self.settings['highestClaimOffset'])
        self.script = "games/oxygen-autoupgrade.py"
        self.prefix = "Oxygen-Auto:"
        self.url = "https://web.telegram.org/k/#@oxygenminerbot"
        self.pot_full = "Filled"
        self.pot_filling = "to fill"
        self.box_claim = "Never."
        self.forceLocalProxy = False
        self.forceRequestUserAgent = False

        super().__init__()

        self.start_app_xpath = "//div[contains(@class, 'reply-markup-row')]//button[.//span[contains(text(), 'Start App')] or .//span[contains(text(), 'Play Now!')]]"

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

        def apply_random_offset(unmodifiedTimer):
            if self.settings['lowestClaimOffset'] <= self.settings['highestClaimOffset']:
                self.random_offset = random.randint(max(self.settings['lowestClaimOffset'], 1), max(self.settings['highestClaimOffset'], 1))
                modifiedTimer = unmodifiedTimer + self.random_offset
                self.output(f"Step {self.step} - Random offset applied to the wait timer of: {self.random_offset} minutes.", 2)
                return modifiedTimer

        self.launch_iframe()
        self.increase_step()

        self.get_balance(True)
        self.increase_step()

        self.output(f"Step {self.step} - The last lucky box claim was attempted on {self.box_claim}.", 2)
        self.increase_step()

        wait_time_text = self.get_wait_time(self.step, "pre-claim") 

        if wait_time_text != self.pot_full:
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
            self.output(f"Step {self.step} - The pre-claim wait time is : {wait_time_text} and random offset is {self.random_offset} minutes.", 1)
            self.increase_step()

            if wait_time_text == self.pot_full or self.settings['forceClaim']:
                try:
                    self.click_claim_button()
                    self.increase_step()

                    self.output(f"Step {self.step} - Waiting 10 seconds for the totals and timer to update...", 3)
                    time.sleep(10)

                    wait_time_text = self.get_wait_time(self.step, "post-claim")
                    matches = re.findall(r'(\d+)([hm])', wait_time_text)
                    total_wait_time = apply_random_offset(sum(int(value) * (60 if unit == 'h' else 1) for value, unit in matches))
                    self.increase_step()

                    self.get_balance(True)
                    self.increase_step()

                    self.output(f"Step {self.step} - check if there are lucky boxes..", 3)
                    xpath = "//div[@class='boxes_cntr']"
                    boxes = self.monitor_element(xpath)
                    self.output(f"Step {self.step} - Detected there are {boxes} boxes to claim.", 3)
                    if int(boxes) > 0:
                        xpath = "//div[@class='boxes_d_wrap']"
                        self.move_and_click(xpath, 10, True, "click the boxes button", self.step, "clickable")
                        xpath = "//div[@class='boxes_d_open' and contains(text(), 'Open box')]"
                        box = self.move_and_click(xpath, 10, True, "open the box...", self.step, "clickable")
                        if box:
                            self.box_claim = datetime.now().strftime("%d %B %Y, %I:%M %p")
                            self.output(f"Step {self.step} - The date and time of the box claim has been updated to {self.box_claim}.", 3)

                    if wait_time_text == self.pot_full:
                        self.output(f"STATUS: The wait timer is still showing: Filled.", 1)
                        self.output(f"Step {self.step} - This means either the claim failed, or there is lag in the game.", 1)
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

    def click_claim_button(self, max_attempts=5, wait_time=10, timeout=10):
        xpath = "//div[@class='farm_btn']"
        for attempt in range(1, max_attempts + 1):
            try:
                button = WebDriverWait(self.driver, timeout).until(
                    EC.presence_of_element_located((By.XPATH, xpath))
                )
                
                self.driver.execute_script("arguments[0].scrollIntoView(true);", button)
                time.sleep(1)
                
                try:
                    self.driver.execute_script("arguments[0].click();", button)
                except Exception:
                    ActionChains(self.driver).move_to_element(button).click().perform()
                
                self.increase_step()
                
                self.output(f"Step {self.step} - Clicked 'Claim' button (Attempt {attempt}). Waiting {wait_time} seconds...", 3)
                time.sleep(wait_time)
                
                try:
                    self.driver.find_element(By.XPATH, xpath)
                except NoSuchElementException:
                    self.output(f"Button XPath changed after {attempt} clicks. Stopping.", 3)
                    break
                    
            except TimeoutException:
                self.output(f"Button not found after {timeout} seconds on attempt {attempt}. Stopping.", 2)
                break
            except ElementClickInterceptedException:
                self.output(f"Button click was intercepted on attempt {attempt}. Trying again.", 2)
                continue
            except Exception as e:
                self.output(f"Error on attempt {attempt}: {str(e)}", 2)
                break

    def get_balance(self, claimed=False):
        prefix = "After" if claimed else "Before"
        default_priority = 2 if claimed else 3

        priority = max(self.settings['verboseLevel'], default_priority)

        balance_text = f'{prefix} BALANCE:'
        oxy_xpath = "//span[@class='oxy_counter']"
        food_xpath = "//div[@class='indicator_item' and @data='food']/div[@class='indicator_text']"

        try:
            oxy_element = self.driver.find_element(By.XPATH, oxy_xpath)
            oxy_balance = oxy_element.text if oxy_element else "N/A"

            food_element = self.driver.find_element(By.XPATH, food_xpath)
            food_balance = food_element.text if food_element else "N/A"

            self.output(f"Step {self.step} - {balance_text} Oxygen: {oxy_balance}, Food: {food_balance}", priority)

            boost_xpath = "(//div[@class='menu_item' and @data='boosts']/div[@class='menu_icon icon_boosts'])[1]"
            boost_element = WebDriverWait(self.driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, boost_xpath))
            )

            actions = ActionChains(self.driver)
            actions.move_to_element(boost_element).click().perform()

            cost_oxy_xpath = "//span[@class='upgrade_price oxy_upgrade']"
            cost_food_xpath = "//span[@class='upgrade_price' and not(contains(@class, 'oxy_upgrade'))]"

            WebDriverWait(self.driver, 10).until(EC.visibility_of_element_located((By.XPATH, cost_oxy_xpath)))

            initial_cost_oxy = self.driver.find_element(By.XPATH, cost_oxy_xpath).text
            initial_cost_food = self.driver.find_element(By.XPATH, cost_food_xpath).text

            self.output(f"Initial Oxygen upgrade cost: {initial_cost_oxy}", 3)
            self.output(f"Initial Food upgrade cost: {initial_cost_food}", 3)

            click_oxy_xpath = "//div[@class='upgrade_btn' and @data='oxy'][1]"
            oxy_upgrade_element = WebDriverWait(self.driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, click_oxy_xpath))
            )
            actions.move_to_element(oxy_upgrade_element).click().perform()

            new_cost_oxy = self.driver.find_element(By.XPATH, cost_oxy_xpath).text
            oxy_upgrade_success = "Success" if new_cost_oxy != initial_cost_oxy else "Failed"
            self.output(f"Oxygen upgrade: {oxy_upgrade_success}", 3)

            click_food_xpath = "//div[@class='upgrade_btn' and @data='food'][1]"
            food_upgrade_element = WebDriverWait(self.driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, click_food_xpath))
            )
            actions.move_to_element(food_upgrade_element).click().perform()

            new_cost_food = self.driver.find_element(By.XPATH, cost_food_xpath).text
            food_upgrade_success = "Success" if new_cost_food != initial_cost_food else "Failed"
            self.output(f"Food upgrade: {food_upgrade_success}", 3)

            return {
                'oxy': oxy_balance,
                'food': food_balance,
                'initial_cost_oxy': initial_cost_oxy,
                'initial_cost_food': initial_cost_food,
                'new_cost_oxy': new_cost_oxy,
                'new_cost_food': new_cost_food,
                'oxy_upgrade_success': oxy_upgrade_success,
                'food_upgrade_success': food_upgrade_success
            }

        except NoSuchElementException:
            self.output(f"Step {self.step} - Element containing '{prefix} Balance:' was not found.", priority)
        except Exception as e:
            self.output(f"Step {self.step} - An error occurred: {str(e)}", priority)

        self.increase_step()

        return None

    def get_wait_time(self, step_number="108", beforeAfter="pre-claim", max_attempts=1):
        for attempt in range(1, max_attempts + 1):
            try:
                self.output(f"Step {self.step} - Get the wait time...", 3)
                xpath = "//div[@class='farm_btn']"
                elements = self.monitor_element(xpath, 10)
                if re.search(r"[СC]ollect food", elements, re.IGNORECASE):
                    return self.pot_full
                xpath = "//div[@class='farm_wait']"
                elements = self.monitor_element(xpath, 10)
                if elements:
                    return elements
                return "Unknown"
            except Exception as e:
                self.output(f"Step {self.step} - An error occurred on attempt {attempt}: {e}", 3)
                return "Unknown"

        return "Unknown"

def main():
    claimer = OxygenAUClaimer()
    claimer.run()

if __name__ == "__main__":
    main()
