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

from mdao import MDAOClaimer

class MDAOAUClaimer(MDAOClaimer):

    def initialize_settings(self):
        super().initialize_settings()
        self.script = "games/mdao-autoupgrade.py"
        self.prefix = "MDAO-Auto:"

    def __init__(self):
        super().__init__()
        self.start_app_xpath = "//span[contains(text(), 'Play')]"

    def attempt_upgrade(self):
        try:
            self.navigate_to_upgrade_tab()
            upgrade_cost = self.get_upgrade_cost()
            available_balance = self.get_available_balance()

            shortfall = available_balance - upgrade_cost
            shortfall_text = f", Shortfall of {round(shortfall, 5)}" if shortfall < 0 else ""
            self.output(f"Step {self.step} - Balance: {available_balance:.1f}, Upgrade cost: {upgrade_cost:.1f}{shortfall_text}", 2)
            self.increase_step()

            if available_balance >= upgrade_cost:
                self.perform_upgrade(upgrade_cost)
            else:
                self.output(f"Step {self.step} - Not enough balance to upgrade. Cost: {upgrade_cost:.1f}, Balance: {available_balance:.1f}", 2)

        except (ValueError, AttributeError, TypeError) as e:
            self.output(f"Step {self.step} - Unable to correctly calculate the upgrade cost. Error: {e}", 2)

        self.increase_step()

    def navigate_to_upgrade_tab(self):
        xpath = "//div[text()='Workbench']"
        self.move_and_click(xpath, 30, True, "look for cost upgrade tab", self.step, "clickable")
        self.output(f"Step {self.step} - Successfully moved to the Workbench tab.", 3)
        self.increase_step()

    def get_upgrade_cost(self):
        xpath = "//div[contains(text(), 'to reach next level')]"
        self.move_and_click(xpath, 30, False, "look upgrade cost in ZP", self.step, "visible")
        upgrade_cost = self.strip_html_and_non_numeric(self.monitor_element(xpath,15,"upgrade cost"))
        self.increase_step()
        return round(float(upgrade_cost) if upgrade_cost else 0, 1)

    def get_available_balance(self):
        xpath = "//div[contains(text(), 'Your balance:')]"
        self.move_and_click(xpath, 30, False, "look available balance in ZP", self.step, "visible")
        available_balance = self.strip_html_and_non_numeric(self.monitor_element(xpath,15,"available ZP"))
        self.increase_step()
        return round(float(available_balance) if available_balance else 0, 1)

    def perform_upgrade(self, upgrade_cost):
        try:
            lvl_up_xpath = "//div[contains(text(), 'LVL UP')]"
            self.move_and_click(lvl_up_xpath, 30, True, "click the LVL UP button", self.step, "clickable")
            self.increase_step()

            confirm_xpath = "//div[contains(text(), 'CONFIRM')]"
            button = self.move_and_click(confirm_xpath, 30, False, "click the Confirm button", self.step, "clickable")
            self.increase_step()
            if button:
                success = self.driver.execute_script("arguments[0].click();", button)
                if success:
                    self.output(f"STATUS: We have spent {upgrade_cost:.1f} ZP to upgrade the mining speed.", 1)

            ok_xpath = "//button[contains(@class, '_btn_16o80_16') and text()='Ok']"
            self.move_and_click(ok_xpath, 20, True, "click the 'Ok' button (maybe not be present)", self.step, "clickable")
            self.increase_step()

        except Exception as e:
            self.output(f"Step {self.step} - Unable to perform upgrade. Error: {e}", 2)

def main():
    claimer = MDAOAUClaimer()
    claimer.run()

if __name__ == "__main__":
    main()
