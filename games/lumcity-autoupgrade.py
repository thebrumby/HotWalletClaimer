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

    def __init__(self):
        super().__init__()
        self.start_app_xpath = "//span[contains(text(), 'Open the App')]"

    def full_claim(self):
        self.step = "100"

        def get_cost_upgrade():
            try:
                balance = float(after_balance) if after_balance else 0
                cost_xpath = "(//div[contains(@class, '_price_lnqn0_57')]/span[1])[1]"
                self.move_and_click(cost_xpath, 30, False, "look for cost upgrade", self.step, "visible")
                cost_upgrade = self.monitor_element(cost_xpath)
                cost_upgrade = float(cost_upgrade.replace(',', '').strip()) if cost_upgrade else 0
            except (ValueError, AttributeError, TypeError) as e:
                self.output(f"Step {self.step} - Unable to convert cost or balance to a number: {e}", 2)
                return

            shortfall = balance - cost_upgrade
            shortfall_text = f", Shortfall of {round(shortfall, 5)}" if shortfall < 0 else ""
            self.output(f"Step {self.step} - Balance: {balance}, Upgrade cost: {cost_upgrade}{shortfall_text}", 2)

            if balance > cost_upgrade:
                self.output(f"Step {self.step} - We can upgrade, processing...", 2)
                perform_upgrade()
            else:
                self.output(f"Step {self.step} - Not enough balance to upgrade. Cost: {cost_upgrade}, Balance: {balance}", 2)

            self.increase_step()

        def perform_upgrade():
            lvl_up_xpath = "//button[contains(@class, '_btn_16o80_16') and text()='Lvl Up']"
            confirm_xpath = "//button[contains(@class, '_btn_16o80_16') and text()='Confirm']"
            ok_xpath = "//button[contains(@class, '_btn_16o80_16') and text()='Ok']"

            self.move_and_click(lvl_up_xpath, 20, True, "click the 'Lvl Up' button", self.step, "clickable")
            self.increase_step()
            
            self.move_and_click(confirm_xpath, 20, True, "click the 'Confirm' button", self.step, "clickable")
            self.increase_step()

            self.move_and_click(ok_xpath, 20, True, "click the 'Ok' button", self.step, "clickable")
            self.increase_step()

        def handle_claim_process():
            xpath = "//button[contains(normalize-space(.), 'Claim')]"
            self.move_and_click(xpath, 20, True, "click the 'Claim' button", self.step, "clickable")
            self.increase_step()

            reward_xpath = "//div[contains(@class, '_msgWrapper_7jeg3_57')]//span[1]"
            reward_value = self.monitor_element(reward_xpath, 20)
            if reward_value:
                self.output(f"Step {self.step} - This claim increased the balance: +{reward_value}", 1)
                try:
                    after_balance = float(before_balance) + float(reward_value)
                except (ValueError, TypeError) as e:
                    self.output(f"Step {self.step} - Error converting balance or reward value to float: {e}", 2)
                    return 60

            ok_xpath = "//div[contains(@class, '_btnContainer')]//button[text()='Ok']"
            self.move_and_click(ok_xpath, 20, True, "click the 'OK' button", self.step, "clickable")
            self.increase_step()

            get_cost_upgrade()
            remaining_wait_time = self.get_wait_time(self.step, "post-claim")
            self.increase_step()

            return remaining_wait_time

        self.launch_iframe()
        self.output(f"Step {self.step} - Short wait to let the totals load", 3)
        time.sleep(10)

        before_balance = self.get_balance(False)
        after_balance = before_balance

        claim_xpath = "//button[contains(normalize-space(.), 'Claim')]"
        self.move_and_click(claim_xpath, 20, True, "move to the 'Claim' screen", self.step, "clickable")

        remaining_wait_time = self.get_wait_time(self.step, "pre-claim")

        try:
            remaining_wait_time = int(remaining_wait_time)
        except ValueError:
            self.output("STATUS: Wait time is unknown due to non-numeric input.", 1)
            return 60

        if remaining_wait_time > 0:
            if remaining_wait_time < 5 or self.settings["forceClaim"]:
                self.settings['forceClaim'] = True
                self.output(f"Step {self.step} - the remaining time to claim is less than the random offset, so applying: settings['forceClaim'] = True", 3)
            else:
                self.output(f"STATUS: Wait time is {remaining_wait_time} minutes and off-set of {self.random_offset}.", 1)
                return remaining_wait_time + self.random_offset

        try:
            if remaining_wait_time < 5 or self.settings['forceClaim']:
                remaining_wait_time = handle_claim_process()

                if remaining_wait_time == 0:
                    self.output(f"Step {self.step} - The wait timer is still showing: Filled.", 1)
                    self.output(f"Step {self.step} - This means either the claim failed, or there is lag in the game.", 1)
                    self.output(f"Step {self.step} - We'll check back in 1 hour to see if the claim processed and if not try again.", 2)
                    return 60
                else:
                    total_time = self.apply_random_offset(remaining_wait_time)
                    self.output(f"STATUS: Pot full in {remaining_wait_time} minutes, plus an off-set of {self.random_offset}.", 1)
                    return total_time
            else:
                if remaining_wait_time:
                    total_time = self.apply_random_offset(remaining_wait_time)
                    self.output(f"Step {self.step} - Not Time to claim this wallet yet. Wait for {total_time} minutes until the storage is filled.", 2)
                    return total_time
                else:
                    self.output(f"Step {self.step} - No wait time data found? Let's check again in one hour.", 2)
                    return 60
        except TimeoutException:
            self.output(f"STATUS: The claim process timed out: Maybe the site has lag? Will retry after one hour.", 1)
            return 60
        except Exception as e:
            self.output(f"STATUS: An error occurred: {e}\nLet's wait an hour and try again", 1)
            return 60

def main():
    claimer = LumCityAUClaimer()
    claimer.run()

if __name__ == "__main__":
    main()