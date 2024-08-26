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
from selenium.common.exceptions import NoSuchElementException, TimeoutException, StaleElementReferenceException, ElementClickInterceptedException, UnexpectedAlertPresentException
from datetime import datetime, timedelta
from selenium.webdriver.chrome.service import Service as ChromeService

from timefarm import TimeFarmClaimer

class TimeFarmAUClaimer(TimeFarmClaimer):

    last_success_timestamp = None  # Class variable to store the timestamp in memory

    def initialize_settings(self):
        super().initialize_settings()
        self.script = "games/timefarm-autostake.py"
        self.prefix = "TimeFarm-AutoStake:"

    def __init__(self):
        super().__init__()
        self.start_app_xpath = "//span[contains(text(), 'Open App')]"

    def save_timestamp(self):
        TimeFarmAUClaimer.last_success_timestamp = datetime.now()

    def load_timestamp(self):
        return TimeFarmAUClaimer.last_success_timestamp

    def stake_coins(self):
        # Check if less than 24 hours have passed since the last successful operation
        last_success = self.load_timestamp()
        if last_success:
            elapsed_time = datetime.now() - last_success
            if elapsed_time < timedelta(hours=24):
                print("Less than 24 hours have passed since the last successful operation.")
                return
        
        # Move to the earn tab
        xpath = "//div[@class='tab-title' and contains(., 'Earn')]"
        success = self.move_and_click(xpath, 20, True, "switch to the 'Earn' tab", self.step, "clickable")
        if not success:
            return
        self.increase_step()

        # Move to the staking tab
        xpath = "//div[@class='title' and contains(., 'Staking')]"
        success = self.move_and_click(xpath, 20, True, "switch to the 'Staking' tab", self.step, "clickable")
        if not success:
            return
        self.increase_step()

        # Let's check if we have an existing claim
        xpath = "(//div[not(contains(@class, 'disabled'))]/div[@class='btn-text' and text()='Claim'])[1]"
        success = self.move_and_click(xpath, 20, True, "try to claim to oldest amount (if any)", self.step, "clickable")
        if success:
            self.output(f"Step {self.step} - We were able to collect the oldest amount.", 3)
        else:
            self.output(f"Step {self.step} - It seems there were no old staking claims to collect.", 3)
        self.increase_step()

        # Click the staking button
        xpath = "//div[@class='btn-text' and (contains(., 'Stake') or contains(., 'Start staking')) and not(ancestor::div[contains(@class, 'disabled')])]"
        success = self.move_and_click(xpath, 20, True, "click the 'Stake' button'", self.step, "clickable")
        if not success:
            self.output(f"Step {self.step} - It appears that no further staking is currently available, restarting browser.", 2)
            self.quit_driver()
            self.launch_iframe()
            return
        self.increase_step()

        # Choose the default (3 days) option by clicking continue
        xpath = "(//div[@class='btn-text' and contains(., 'Continue')])[1]"
        success = self.move_and_click(xpath, 20, True, "click the 'Continue' button'", self.step, "clickable")
        if not success:
            return
        self.increase_step()

        # Select the Max option
        xpath = "//div[@class='percent' and contains(., 'MAX')]"
        success = self.move_and_click(xpath, 20, True, "click the 'MAX' option'", self.step, "clickable")
        if not success:
            return
        self.increase_step()

        # Click the "Continue" button
        xpath = "(//div[@class='btn-text' and contains(., 'Continue')])[2]"
        success = self.move_and_click(xpath, 20, True, "click the 'Continue' button'", self.step, "clickable")
        if not success:
            self.output(f"Step {self.step} - It appears that no further staking is currently available, restarting browser.", 2)
            self.quit_driver()
            self.launch_iframe()
            return
        self.increase_step()

        # Click the "Stake" button
        xpath = "//div[@class='btn-text' and contains(., 'Stake')]"
        success = self.move_and_click(xpath, 20, True, "click the 'Stake' button'", self.step, "clickable")
        if not success:
            self.output(f"Step {self.step} - It appears that no further staking is currently available, restarting browser.", 2)
            self.quit_driver()
            self.launch_iframe()
            return
        self.increase_step()

        xpath = "//*[contains(text(), \"You've successfully\")]"
        if self.move_and_click(xpath, 5, False, "check for success", self.step, "visible"):
            self.output(f"STATUS: We clicked the Staking link and it confirmed success.", 1)
            self.increase_step()
            self.save_timestamp()  # Save the timestamp after success
            return "3-day Stake Successful. "
        else:
            self.output(f"STATUS: We clicked the Staking link (3-day time/max available coins).", 1)
            self.increase_step()
            return "Staking attempted. "

def main():
    claimer = TimeFarmAUClaimer()
    claimer.run()

if __name__ == "__main__":
    main()
