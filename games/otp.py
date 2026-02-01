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

from claimer_improved import Claimer

class OTPFinder(Claimer):

    def initialize_settings(self):
        super().initialize_settings()
        self.script = "games/cold.py"
        self.prefix = "BNB-Cold:"
        self.url = "https://web.telegram.org/k/#777000"
        self.pot_full = "Filled"
        self.pot_filling = "Mining"
        self.seed_phrase = None
        self.forceLocalProxy = False
        self.forceRequestUserAgent = False
        self.start_app_xpath = "//button//span[contains(text(), 'Open Wallet')]"

    def __init__(self):
        self.settings_file = "variables.txt"
        self.status_file_path = "status.txt"
        self.wallet_id = ""
        self.load_settings()
        self.random_offset = random.randint(self.settings['lowestClaimOffset'], self.settings['highestClaimOffset'])
        super().__init__()


    def next_steps(self):
        # Initialise Chrome/Chromium & load the login notification service user (ID 777000)
        self.step = "01"
        self.driver = self.get_driver()
        self.driver.get(self.url)
        # Check for the last OTP & Print it
        xpath = "(//span[@class='translatable-message'])[last()]"
        self.target_element = self.move_and_click(xpath,10, False, "read the last OTP code ", "08", "visible")
        OTP = self.monitor_element(xpath, 10, "grab the last OTP")
        OTP = self.strip_html_and_non_numeric(OTP)
        print(f"The most recent OTP was: {OTP}")
        # Close the session
        self.quit_driver()

def main():
    claimer = OTPFinder()
    claimer.run()

if __name__ == "__main__":
    main()