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

from tabizoo import TabizooClaimer

class TabizooAUClaimer(TabizooClaimer):
    def initialize_settings(self):
        super().initialize_settings()
        self.script = "games/tabizoo-autoupgrade.py"
        self.prefix = "TabiZoo-AutoUpgrade:"

    def __init__(self):
        super().__init__()

    def attempt_upgrade(self, balance):
        try:
            start_lvl = None
            end_lvl = None
            # attempts one upgrade per claim session
            xpath = "//span[contains(text(), 'Lv')]"
            current_level = self.monitor_element(xpath, 15, "current level")
            original_balance = balance
            self.increase_step()
            if current_level:
                self.output(f"Step {self.step} - Current level is: {current_level}", 2)

            xpath = "//span[contains(text(), 'Lv.')]"
            if self.brute_click(xpath, 10, "click the 'Upgrade' tab"):
                self.increase_step()

                xpath = "//label[text()='Consume']/following-sibling::p//span"
                upgrade_cost = None
                upgrade_cost = self.monitor_element(xpath, 15, "upgrade cost")
                self.increase_step()
                if upgrade_cost:
                    self.output(f"Step {self.step} - Upgrade cost is: {upgrade_cost}", 3)

                xpath = "//div[text()='Insufficient Balance']"
                no_money = self.move_and_click(xpath, 10, False, "check if we have enough funds (timeout means we have enough!)", self.step, "clickable")
                self.increase_step()
                if no_money:
                    self.output(f"Step {self.step} - Upgrade costs {upgrade_cost} but you only have {balance}.", 3)
                    return

                for attempt in range(3):
                    xpath = "//div[text()='Upgrade']"
                    self.brute_click(xpath, 10, f"attempt {attempt+1} to click the 'Upgrade' button")
                    self.increase_step()
                    
                    # Check if the upgrade cost increased
                    new_upgrade_cost = self.monitor_element("//label[text()='Consume']/following-sibling::p//span", 10, "upgrade cost after click")
                    
                    if new_upgrade_cost and new_upgrade_cost != upgrade_cost:
                        break  # Exit the loop if the cost changed, meaning the upgrade likely went through

                self.quit_driver()
                self.launch_iframe()
                xpath = "//span[contains(text(), 'Lv')]"
                new_level = self.monitor_element(xpath, 15, "current level")
                self.increase_step()

                if current_level:
                    start_lvl = float(self.strip_html_and_non_numeric(current_level))
                if new_level:
                    end_lvl = float(self.strip_html_and_non_numeric(new_level))

                if start_lvl and new_level:
                    if end_lvl > start_lvl:
                        self.output(f"STATUS: Upgraded from {current_level} to {new_level} at a cost of {upgrade_cost}.", 2)
                    else:
                        self.output(f"Step {self.step} - Looks like the upgrade sequence failed.", 2)
                else:
                    self.output(f"Step {self.step} - We failed to read some of the levels.", 2)

        except NoSuchElementException as e:
            self.output(f"Step {self.step} - Element not found: {str(e)}", 1)
        except TimeoutException as e:
            self.output(f"Step {self.step} - Timeout occurred: {str(e)}", 1)
        except ElementClickInterceptedException as e:
            self.output(f"Step {self.step} - Click was intercepted: {str(e)}", 1)
        except Exception as e:
            self.output(f"Step {self.step} - An unexpected error occurred: {str(e)}", 1)

def main():
    claimer = TabizooAUClaimer()
    claimer.run()

if __name__ == "__main__":
    main()