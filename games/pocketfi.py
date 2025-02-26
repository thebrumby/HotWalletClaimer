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

class PocketFiClaimer(Claimer):

    def initialize_settings(self):
        super().initialize_settings()
        self.script = "games/pocketfi.py"
        self.prefix = "Pocketfi:"
        self.url = "https://web.telegram.org/k/#@pocketfi_bot"
        self.pot_full = "Filled"
        self.pot_filling = "to fill"
        self.seed_phrase = None
        self.forceLocalProxy = False
        self.forceRequestUserAgent = False
        self.start_app_xpath = "//div[contains(@class, 'reply-markup-row')]//span[contains(., 'Mining') or contains(., 'PocketFi')]"
        self.balance_xpath = f"//span[@class='text-2xl font-bold']"
        self.time_remaining_xpath = "//p[contains(text(), 'burn in')]"

    def __init__(self):
        self.settings_file = "variables.txt"
        self.status_file_path = "status.txt"
        self.wallet_id = ""
        self.load_settings()
        self.random_offset = -60
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

        self.launch_iframe()
        self.increase_step()

        button_texts = [
            "What simple actions?",
            "What else is here?",
            "Start mining"
        ]
        
        for text in button_texts:
            xpath = f"//button[normalize-space(.)='{text}']"
            button = self.move_and_click(xpath, 15, True, f"click '{text}'", self.step, "clickable")
            if button:
                self.increase_step()
            else:
                self.output(f"Step {self.step} - Button with text '{text}' not found. Let's attempt to claim.", 3)
                break


        self.get_balance(self.balance_xpath, False)
        self.increase_step()

        wait_time_text_pre = self.get_wait_time(self.time_remaining_xpath, "108", "pre-claim")
        if wait_time_text_pre is False:
            self.output("STATUS: Failed to retrieve pre-claim wait time. Let's retry in 1 hour.", 1)
            return 60
        
        if wait_time_text_pre > 330:
            actual_wait_time = wait_time_text_pre - 10 
            self.output(f"STATUS: Looks like the pot isn't ready to claim for {wait_time_text_pre} minutes. Let's come back in {actual_wait_time} minutes.", 1)
            return actual_wait_time
        
        self.output(f"Step {self.step} - the pre-claim timer shows {wait_time_text_pre} minutes until burn.", 2)
        
        xpath = "//div[@class='absolute flex items-center justify-center flex-col text-white']/span[contains(text(), 'claim')]"
        clicked_it = False
        button = self.brute_click(xpath, 30, "click claim")
        if button:
            self.output(f"Step {self.step} - We may have clicked, let's confirm with the timer.", 3)
            possible_click = True
        else:
            self.output(f"Step {self.step} - No button found to click.", 3)
        
        time.sleep(5)
        wait_time_text_mid = self.get_wait_time(self.time_remaining_xpath, "108", "mid-claim")
        if wait_time_text_mid is False:
            self.output("STATUS: Failed to retrieve post-claim wait time. Let's retry in 1 hour.", 1)
            return 60
        if possible_click and wait_time_text_mid > 330:
            self.output(f"Step {self.step} - Looks like we made the claim.", 3)
            clicked_it = True
        else:
            self.output(f"Step {self.step} - Looks like we failed the claim.", 3)

        self.increase_step()
        
        self.get_balance(self.balance_xpath, True)
        self.increase_step()

        self.get_profit_hour(True)
        
        if wait_time_text_mid:
            next_claim = max(5, wait_time_text_mid-10) 

        if clicked_it and next_claim:
            self.output(f"STATUS: Successfully claimed. Mine again in {next_claim} minutes.", 1)
            return next_claim

        if next_claim:
            self.output(f"STATUS: No claim this time. Let's try to mine again in {next_claim} minutes.", 1)
            return next_claim
        
        self.output(f"STATUS: Issues with making the claim, let's come back in an hour.", 1)
        return 60

    def get_profit_hour(self, claimed=False):
        prefix = "After" if claimed else "Before"
        default_priority = 2 if claimed else 3

        priority = max(self.settings['verboseLevel'], default_priority)

        # Construct the specific profit XPath
        profit_text = f'{prefix} PROFIT/HOUR:'
        profit_xpath = "//p[contains(., '$SWITCH')]//span[last()]"

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
    claimer = PocketFiClaimer()
    claimer.run()

if __name__ == "__main__":
    main()
