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

    def attempt_upgrade(self):
        try:
            # attempts one upgrade per claim session
            xpath = "//span[contains(text(), 'Lv')]"
            current_level = self.monitor_element(xpath, 15, "current level")
            self.increase_step()
            if current_level:
                self.output(f"Step {self.step} - Current level is: {current_level}", 2)

            xpath = "//img[contains(@src, 'upgrade_icon')]"
            if self.move_and_click(xpath, 10, True, "click the 'upgrade' button", self.step, "clickable"):
                self.increase_step()
                xpath = "//img[contains(@src, 'coin')]/following-sibling::span"
                upgrade_cost = self.monitor_element(xpath, 15, "upgrade cost")
                self.increase_step()
                if upgrade_cost:
                    self.output(f"Step {self.step} - Upgrade cost is: {upgrade_cost}", 2)

                xpath = "//div[text()='Upgrade']"
                self.move_and_click(xpath, 10, True, "click the 'upgrade' confirmation button", self.step, "clickable")
                self.increase_step()

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