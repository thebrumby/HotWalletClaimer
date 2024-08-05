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

from lumcity import LumCityClaimer

class LumCityAUClaimer(LumCityClaimer):

    def initialize_settings(self):
        super().initialize_settings()
        self.script = "games/lumcity-autoupgrade.py"
        self.prefix = "LumCity-Auto:"
        self.allow_early_claim = False

    def __init__(self):
        super().__init__()
        self.start_app_xpath = "//span[contains(text(), 'Open the App')]"

    def attempt_upgrade(self, balance):
        try:
            cost_upgrade = self.get_upgrade_cost()
        except (ValueError, AttributeError, TypeError) as e:
            self.output(f"Step {self.step} - Unable to convert cost or balance to a number: {e}", 2)
            return

        shortfall = balance - cost_upgrade
        shortfall_text = f", Shortfall of {round(shortfall, 5)}" if shortfall < 0 else ""
        self.output(f"Step {self.step} - Balance: {balance}, Upgrade cost: {cost_upgrade}{shortfall_text}", 2)

        if balance > cost_upgrade:
            self.output(f"Step {self.step} - We can upgrade, processing...", 2)
            self.perform_upgrade()
        else:
            self.output(f"Step {self.step} - Not enough balance to upgrade. Cost: {cost_upgrade}, Balance: {balance}", 2)

        self.increase_step()

    def get_upgrade_cost(self):
        cost_xpath = "(//div[contains(@class, '_price_lnqn0_57')]/span[1])[1]"
        self.move_and_click(cost_xpath, 30, False, "look for cost upgrade", self.step, "visible")
        cost_upgrade = self.monitor_element(cost_xpath)
        return float(cost_upgrade.replace(',', '').strip()) if cost_upgrade else 0

    def perform_upgrade(self):
        try:
            lvl_up_xpath = "//button[contains(@class, '_btn_16o80_16') and text()='Lvl Up']"
            confirm_xpath = "//button[contains(@class, '_btn_16o80_16') and text()='Confirm']"
            ok_xpath = "//button[contains(@class, '_btn_16o80_16') and text()='Ok']"

            self.move_and_click(lvl_up_xpath, 20, True, "click the 'Lvl Up' button", self.step, "clickable")
            self.increase_step()

            self.move_and_click(confirm_xpath, 20, True, "click the 'Confirm' button", self.step, "clickable")
            self.increase_step()

            self.move_and_click(ok_xpath, 20, True, "click the 'Ok' button", self.step, "clickable")
            self.increase_step()

            self.output(f"STATUS: Upgrade performed successfully.", 1)
        except Exception as e:
            self.output(f"Step {self.step} - Unable to perform upgrade. Error: {e}", 2)

def main():
    claimer = LumCityAUClaimer()
    claimer.run()

if __name__ == "__main__":
    main()