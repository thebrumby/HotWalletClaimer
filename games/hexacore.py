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

class HexacoreClaimer(Claimer):

    def initialize_settings(self):
        super().initialize_settings()
        self.script = "games/hexacore.py"
        self.prefix = "Hexacore:"
        self.url = "https://web.telegram.org/k/#@HexacoinBot"
        self.pot_full = "Filled"
        self.pot_filling = "to fill"
        self.seed_phrase = None
        self.forceLocalProxy = False
        self.forceRequestUserAgent = True
        self.start_app_xpath = "//div[contains(@class, 'reply-markup-row')]//a[contains(@href, 'https://t.me/HexacoinBot/wallet?startapp=play')]"

    def __init__(self):
        super().__init__()  # Call the parent class's constructor
        self.settings_file = "variables.txt"
        self.status_file_path = "status.txt"
        self.wallet_id = ""
        self.load_settings()
        self.random_offset = random.randint(self.settings['lowestClaimOffset'], self.settings['highestClaimOffset'])

    def next_steps(self):
        if hasattr(self, 'step'):
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

        self.launch_iframe()

        xpath = "//div[@id='modal-root']//button[contains(@class, 'IconButton_button__')]"
        self.move_and_click(xpath, 10, True, "remove overlays", self.step, "visible")
        self.increase_step()

        time.sleep(5)

        xpath = "//div[contains(@class, 'NavBar_agoContainer')]"
        self.move_and_click(xpath, 10, True, "click main tab", self.step, "visible")
        self.increase_step()
        self.daily_claim()
        self.get_balance(False)
 
        remains = self.get_remains()
        if remains:
            self.output(f"Step {self.step} - The system reports {remains} available to click.", 2)
            wait_time_text = self.pot_full
        else:
            self.output(f"Step {self.step} - There doesn't appear to be any remaining clicks available.", 2)
            wait_time_text = self.get_wait_time(self.step, "pre-claim") 
        self.increase_step()

        if wait_time_text != self.pot_full:
            matches = re.findall(r'(\d+)([hm])', wait_time_text)
            remaining_wait_time = sum(int(value) * (60 if unit == 'h' else 1) for value, unit in matches)
            if remaining_wait_time < 5 or self.settings["forceClaim"]:
                self.settings['forceClaim'] = True
                self.output(f"Step {self.step} - the remaining time to claim is less than the random offset, so applying: settings['forceClaim'] = True", 3)
            else:
                optimal_time = min(15, remaining_wait_time)
                self.output(f"STATUS: Box due in {box_time} mins, and more clicks in {remaining_wait_time} mins, so sleeping for {optimal_time} mins.", 1)
                return optimal_time

        if wait_time_text:
            return 360

        try:
            self.output(f"Step {self.step} - The pre-claim wait time is : {wait_time_text} and random offset is {self.random_offset} minutes.", 1)
            self.increase_step()

            if wait_time_text == self.pot_full or self.settings['forceClaim']:
                try:
                    self.click_ahoy(remains)

                    self.output(f"Step {self.step} - Waiting 10 seconds for the totals and timer to update...", 3)
                    time.sleep(10)

                    wait_time_text = self.get_wait_time(self.step, "post-claim")
                    matches = re.findall(r'(\d+)([hm])', wait_time_text)
                    total_wait_time = self.apply_random_offset(sum(int(value) * (60 if unit == 'h' else 1) for value, unit in matches))
                    self.increase_step()

                    if wait_time_text == self.pot_full:
                        self.output(f"STATUS: The wait timer is still showing: Filled.", 1)
                        self.output(f"Step {self.step} - This means either the claim failed, or there is lag in the game.", 1)
                        self.output(f"Step {self.step} - We'll check back in 1 hour to see if the claim processed and if not try again.", 2)
                    else:
                        optimal_time = min(30, total_wait_time)
                        self.output(f"STATUS: Successful claim! More clicks in {total_wait_time} mins. Sleeping for {max(60, optimal_time)} mins.", 1)
                    return max(60, optimal_time)

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
            
    def daily_claim(self):
        xpath = "//div[@class='DailyClaimButton_redDot__zH5Kc']"
        success = self.move_and_click(xpath, 10, True, "Click on daily reward", self.step, "visible")
        
        if success:
            print("Daily reward button clicked successfully.")
            
            # XPath for the 'Claim Reward' button
            xpath = "//button[contains(@class, 'DailyClaimModal_button__c-C7Y') and not(@disabled) and contains(text(), 'Claim Reward')]"
            
            # Attempt to click the 'Claim Reward' button
            if self.move_and_click(xpath, 10, True, "Click on claim daily reward", self.step, "visible"):
                print("Claim daily reward button clicked successfully.")
            else:
                print("Failed to click on the claim daily reward button.")
        else:
            print("Failed to click on the daily reward button Maybe already claimed .")    
            
    def get_remains(self):
        remains_xpath = "//p[contains(text(), 'Remains')]/span"
        try:
            # Move to and click the element if necessary
            first = self.move_and_click(remains_xpath, 10, False, "remove overlays", self.step, "visible")
            
            # Monitor the element to get its content
            remains_element = self.monitor_element(remains_xpath)
            
            # Check if the remains_element is found and get its text content
            if remains_element:
                if remains_element.isdigit():
                    return int(remains_element)
                else:
                    self.output(f"Step {self.step} - The text '{remains_text}' is not a valid number.", 3)
                    return None
            else:
                return None
        except NoSuchElementException:
            # Handle the case where the element is not found
            self.output(f"Step {self.step} - Element containing 'Remains' was not found.", 3)
            return None
        except Exception as e:
            # Handle any other exceptions that might occur
            self.output(f"Step {self.step} - An error occurred: {str(e)}", 3)
            return None
        
    def click_ahoy(self, remains):
        xpath = "//p[contains(text(), 'Remains')]"
        self.output(f"Step {self.step} - We have {remains} targets to click. This might take some time!", 3)
    
        try:
            element = self.driver.find_element(By.XPATH, xpath)
        except Exception as e:
            self.output(f"Step {self.step} - Error finding element: {str(e)}", 2)
            return None

        random_y = random.randint(100, 180)
        random_x = random.randint(-20, 20)

        action = ActionChains(self.driver)
        action.move_to_element_with_offset(element, random_x, random_y).perform()

        if not isinstance(remains, (int, float)):
            self.output(f"Step {self.step} - Invalid type for 'remains': {type(remains).__name__}", 2)
            return None 

        click_count = 0
        max_clicks = 500
        start_time = time.time()

        while remains > 0 and click_count < max_clicks and (time.time() - start_time) < 3600:
            try:
                script = f"""
                var elem = document.elementFromPoint({random_x}, {random_y});
                if (elem) {{
                    var event = new PointerEvent('pointerdown', {{
                        pointerId: 1,
                        bubbles: true,
                        cancelable: true,
                        view: window,
                        detail: 1,
                        screenX: window.screenX + {random_x},
                        screenY: window.screenY + {random_y},
                        clientX: {random_x},
                        clientY: {random_y},
                        button: 0,
                        buttons: 1,
                        pointerType: 'touch'
                    }});
                    elem.dispatchEvent(event);

                    var eventUp = new PointerEvent('pointerup', {{
                        pointerId: 1,
                        bubbles: true,
                        cancelable: true,
                        view: window,
                        detail: 1,
                        screenX: window.screenX + {random_x},
                        screenY: window.screenY + {random_y},
                        clientX: {random_x},
                        clientY: {random_y},
                        button: 0,
                        buttons: 1,
                        pointerType: 'touch'
                    }});
                    elem.dispatchEvent(eventUp);
                }}
                """
                self.driver.execute_script(script)
            except Exception as e:
                self.output(f"Step {self.step} - Error executing JS tap: {str(e)}", 2)

            remains -= 1
            click_count += 1

            if remains % 100 == 0:
                self.output(f"Step {self.step} - {remains} clicks remaining...", 2)

            time.sleep(random.uniform(0.05, 0.15))  # Random delay between taps

        if remains > 0:
            self.output(f"Step {self.step} - Reached {click_count} clicks or 1 hour limit, returning early.", 2)
        else:
            self.output(f"Step {self.step} - Completed all clicks within limit.", 2)


    def get_balance(self, claimed=False):
        prefix = "After" if claimed else "Before"
        default_priority = 2 if claimed else 3

        priority = max(self.settings['verboseLevel'], default_priority)

        balance_text = f'{prefix} BALANCE:'
        balance_xpath = "//div[contains(@class, 'BalanceDisplay_value')]"

        try:
            # Move to and click the element if necessary
            first = self.move_and_click(balance_xpath, 30, False, "remove overlays", self.step, "visible")

            # Monitor the element to get its content
            element = self.monitor_element(balance_xpath)
        
            if element:
                # Extract the text content of the balance element
                balance_value = element
                self.output(f"Step {self.step} - {balance_text} {balance_value}", priority)
                self.increase_step()
                return balance_value
            else:
                self.output(f"Step {self.step} - Element for balance not found or has no text.", priority)
                return None

        except NoSuchElementException:
            self.output(f"Step {self.step} - Element containing '{balance_text}' was not found.", priority)
        except Exception as e:
            self.output(f"Step {self.step} - An error occurred: {str(e)}", priority)

        self.increase_step()
        return None

    def get_wait_time(self, step_number="108", beforeAfter="pre-claim", max_attempts=1):
        for attempt in range(1, max_attempts + 1):
            try:
                self.output(f"Step {self.step} - Get the wait time...", 3)
                xpath = "//span[contains(text(), 'TAPS IN')]"
                elements = self.monitor_element(xpath, 10)
                if elements:
                    parts = elements.split("TAPS IN ")
                    return parts[1] if len(parts) > 1 else False
                return self.pot_full
            except Exception as e:
                self.output(f"Step {self.step} - An error occurred on attempt {attempt}: {e}", 3)
                return False
        return False

def main():
    claimer = HexacoreClaimer()
    claimer.run()

if __name__ == "__main__":
    main()
