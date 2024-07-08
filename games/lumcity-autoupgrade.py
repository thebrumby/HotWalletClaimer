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

class LumCityAUClaimer(Claimer):

    def __init__(self):
        self.settings_file = "variables.txt"
        self.status_file_path = "status.txt"
        self.load_settings()
        self.random_offset = random.randint(max(self.settings['lowestClaimOffset'], 0), max(self.settings['highestClaimOffset'], 0))
        self.script = "games/lumcity-autoupgrade.py"
        self.prefix = "LumCity-Auto:"
        self.url = "https://web.telegram.org/k/#@LumCity_bot"
        self.pot_full = "Filled"
        self.pot_filling = "to fill"
        self.seed_phrase = None
        self.forceLocalProxy = False
        self.forceRequestUserAgent = False

        super().__init__()

        self.start_app_xpath = "//span[contains(text(), 'Open the App')]"

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

        def get_cost_upgrade():
            balance = float(after_balance)
            cost_xpath = "//div[contains(@class, '_price_lnqn0_57')]/span[1]"

            try:
                self.move_and_click(cost_xpath, 30, False, "look for cost upgrade", self.step, "visible")
                cost_upgrade = self.monitor_element(cost_xpath)
                
                try:
                    cost_upgrade = float(cost_upgrade.replace(',', '').strip())
                except (ValueError, AttributeError):
                    self.output(f"Step {self.step} - Unable to convert cost '{cost_upgrade}' to a number.", 2)
                    return

                if balance is None or not isinstance(balance, (int, float)):
                    self.output(f"Step {self.step} - Invalid balance: {balance}", 2)
                    return

                shortfall = balance - cost_upgrade
                if shortfall < 0:
                    shortfall_text = f", Shortfall of {round(shortfall, 5)}"
                else:
                    shortfall_text = ""
                self.output(f"Step {self.step} - Balance: {balance}, Upgrade cost: {cost_upgrade}{shortfall_text}", 2)

                if balance > cost_upgrade:
                    self.output(f"Step {self.step} - We can upgrade, processing...", 2)
                    perform_upgrade()
                else:
                    self.output(f"Step {self.step} - Not enough balance to upgrade. Cost: {cost_upgrade}, Balance: {balance}", 2)

            except NoSuchElementException:
                self.output(f"Step {self.step} - Element containing cost upgrade was not found.", 2)
            except Exception as e:
                self.output(f"Step {self.step} - An error occurred: {str(e)}", 2)

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

        def apply_random_offset(unmodified_timer):
            if self.settings['lowestClaimOffset'] <= self.settings['highestClaimOffset']:
                self.random_offset = random.randint(self.settings['lowestClaimOffset'], self.settings['highestClaimOffset'])
                modified_timer = unmodified_timer + self.random_offset
                self.output(f"Step {self.step} - Random offset applied to the wait timer of: {self.random_offset} minutes.", 2)
                return modified_timer
            return unmodified_timer

        def handle_claim_process():
            xpath = "//button[contains(normalize-space(.), 'Claim')]"
            self.move_and_click(xpath, 20, True, "click the 'Claim' button", self.step, "clickable")
            self.increase_step()

            reward_xpath = "//div[contains(@class, '_msgWrapper_7jeg3_57')]//span[1]"
            reward_value = self.monitor_element(reward_xpath, 20)
            if reward_value:
                self.output(f"Step {self.step} - This claim increased the balance: +{reward_value}", 1)
                after_balance = float(before_balance) + float(reward_value)

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

        if remaining_wait_time > 0:
          try:
            if remaining_wait_time < 5 or self.settings["forceClaim"]:
                  self.settings['forceClaim'] = True
                  self.output(f"Step {self.step} - the remaining time to claim is less than the random offset, so applying: settings['forceClaim'] = True", 3)
            else:
                  self.output(f"STATUS: Wait time is {remaining_wait_time} minutes and off-set of {self.random_offset}.", 1)
                  return remaining_wait_time + self.random_offset
          except ValueError:
              self.output("STATUS: Wait time is unknown due to non-numeric input.", 1)
              return 60

        try:
            if remaining_wait_time < 5 or self.settings['forceClaim']:
                remaining_wait_time = handle_claim_process()

                if remaining_wait_time == 0:
                    self.output(f"Step {self.step} - The wait timer is still showing: Filled.", 1)
                    self.output(f"Step {self.step} - This means either the claim failed, or there is lag in the game.", 1)
                    self.output(f"Step {self.step} - We'll check back in 1 hour to see if the claim processed and if not try again.", 2)
                    return 60
                else:
                    total_time = apply_random_offset(remaining_wait_time)
                    self.output(f"STATUS: Pot full in {remaining_wait_time} minutes, plus an off-set of {self.random_offset}.", 1)
                    return total_time
            else:
                if remaining_wait_time:
                    total_time = apply_random_offset(remaining_wait_time)
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

    def get_balance(self, claimed=False):
        prefix = "After" if claimed else "Before"
        default_priority = 2 if claimed else 3

        priority = max(self.settings['verboseLevel'], default_priority)

        balance_text = f'{prefix} Golt BALANCE:' if claimed else f'{prefix} BALANCE:'
        balance_xpath = f"(//div[contains(@class, '1615f_24')])[2]"
        balance_part = None

        try:
            self.move_and_click(balance_xpath, 30, False, "look for Golt balance", self.step, "visible")
            balance_part = self.strip_html_tags(self.monitor_element(balance_xpath))
            self.output(f"Step {self.step} - {balance_text} {balance_part}", priority)
        except NoSuchElementException:
            self.output(f"Step {self.step} - Element containing '{prefix} Balance:' was not found.", priority)
        except Exception as e:
            self.output(f"Step {self.step} - An error occurred: {str(e)}", priority)

        self.increase_step()

    def strip_html_tags(self, text):
        clean = re.compile('<.*?>')
        text_without_html = re.sub(clean, '', text)
        text_cleaned = re.sub(r'[^0-9:.]', '', text_without_html)
        return text_cleaned

    def extract_time(self, text):
        time_parts = text.split(':')
        if len(time_parts) == 3:
            try:
                hours = int(time_parts[0].strip())
                minutes = int(time_parts[1].strip())
                return hours * 60 + minutes
            except ValueError:
                return "Unknown"
        return "Unknown"

    def get_wait_time(self, step_number="108", beforeAfter="pre-claim", max_attempts=1):
        for attempt in range(1, max_attempts + 1):
            try:
                self.output(f"Step {self.step} - check if the timer is elapsing...", 3)
                xpath = "//span[text()='Fill Time']/ancestor::div[1]/following-sibling::div"
                pot_full_value = self.extract_time(self.strip_html_tags(self.monitor_element(xpath, 15)))
                return pot_full_value
            except Exception as e:
                self.output(f"Step {self.step} - An error occurred on attempt {attempt}: {e}", 3)
                return "Unknown"
        return "Unknown"

def main():
    claimer = LumCityAUClaimer()
    claimer.run()

if __name__ == "__main__":
    main()