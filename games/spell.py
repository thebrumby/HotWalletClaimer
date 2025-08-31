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

import requests
import urllib.request
from claimer import Claimer

class SpellClaimer(Claimer):

    def initialize_settings(self):
        super().initialize_settings()
        self.script = "games/spell.py"
        self.prefix = "Spell:"
        self.url = "https://web.telegram.org/k/#@spell_wallet_bot"
        self.pot_full = "Filled"
        self.pot_filling = "to fill"
        self.seed_phrase = None
        self.forceLocalProxy = False
        self.forceRequestUserAgent = False
        self.allow_early_claim = False
        self.start_app_xpath = "//div[@class='reply-markup-row']//span[contains(text(),'Open Spell')]"
        self.start_app_menu_item = "//a[.//span[contains(@class, 'peer-title') and normalize-space(text())='Spell Wallet']]"

    def charge_until_complete(self, max_seconds: float = 10.0, pause: float = 0.25) -> bool:
        """
        Repeatedly click the 'Charging…' claim button for up to max_seconds.
        Stops early if progress hits 100% or the 'Spin the Wheel' UI appears.
        Returns True if we likely completed the charge, else False.
        """
        start = time.time()
    
        # robust selectors for the same button/state
        charging_xpaths = [
            # Button with explicit "Charging..."
            "//button[.//p[normalize-space()='Charging...']]",
    
            # Button that has a progressbar + a 'Charging' label
            "//button[.//div[@role='progressbar'] and .//p[contains(normalize-space(),'Charging')]]",
    
            # Button that owns a progressbar with a numeric value (1..99)
            "//div[@role='progressbar' and number(@aria-valuenow) >= 1 and number(@aria-valuenow) < 100]/ancestor::button[1]",
    
            # Button showing a percent label (e.g. 20%)
            "//button[.//div[@role='progressbar'] and .//div[contains(normalize-space(.), '%')]]",
        ]
    
        # quick checks for "done" states
        spin_xpath   = "//p[contains(normalize-space(.), 'Spin the Wheel')]"
        percent_node = "//div[@role='progressbar' and @aria-valuenow]"
    
        def read_progress() -> float | None:
            try:
                el = self.driver.find_element(By.XPATH, percent_node)
                val = el.get_attribute("aria-valuenow")
                return float(val) if val is not None else None
            except Exception:
                return None
    
        while time.time() - start < max_seconds:
            # finished already?
            try:
                if self.driver.find_elements(By.XPATH, spin_xpath):
                    self.output(f"Step {self.step} - Wheel appeared; charging complete.", 3)
                    return True
            except Exception:
                pass
    
            prog = read_progress()
            if prog is not None and prog >= 100:
                self.output(f"Step {self.step} - Progress {prog:.0f}% reached; charging complete.", 3)
                return True
    
            # try each selector and click once
            clicked_this_cycle = False
            for xp in charging_xpaths:
                try:
                    btn = self.driver.find_element(By.XPATH, xp)
                    # keep it simple & fast: try native, then JS
                    try:
                        ActionChains(self.driver).move_to_element(btn).pause(0.02).click(btn).perform()
                        clicked_this_cycle = True
                        break
                    except Exception:
                        try:
                            self.driver.execute_script("arguments[0].click();", btn)
                            clicked_this_cycle = True
                            break
                        except Exception:
                            continue
                except Exception:
                    continue
    
            if not clicked_this_cycle:
                # small diagnostic (low noise)
                if self.settings.get('debugIsOn'):
                    self.debug_information("Charging button not found this tick", "warning")
            time.sleep(pause)
    
        self.output(f"Step {self.step} - Charging loop ended after {max_seconds}s without clear completion.", 2)
        return False

    def spell_accept_and_continue(self):
        try:
            checkbox_xpath = "//span[@aria-hidden='true' and contains(@class,'chakra-checkbox__control')]"
            btn_xpath = "//button[contains(@class,'chakra-button') and normalize-space()='Get Started']"
    
            # Find the checkbox
            checkbox = self.driver.find_element(By.XPATH, checkbox_xpath)
    
            # Scroll into view and synthesize a real click
            self.driver.execute_script("""
                const el = arguments[0];
                el.scrollIntoView({block:'center', inline:'center'});
                const rect = el.getBoundingClientRect();
                const x = rect.left + rect.width / 2;
                const y = rect.top + rect.height / 2;
                ['pointerdown','mousedown','mouseup','click'].forEach(type => {
                  el.dispatchEvent(new MouseEvent(type, {bubbles:true, cancelable:true, clientX:x, clientY:y}));
                });
            """, checkbox)
    
            time.sleep(0.5)
    
            # Verify that it toggled
            if checkbox.get_attribute("data-checked") is not None:
                self.output(f"Step {self.step} - Checkbox ticked successfully.", 2)
    
                # Now click "Get Started"
                btn = self.driver.find_element(By.XPATH, btn_xpath)
                self.driver.execute_script("arguments[0].click();", btn)
                self.output(f"Step {self.step} - Clicked 'Get Started'.", 2)
                return True
            else:
                self.output(f"Step {self.step} - Checkbox not ticked after click attempt.", 1)
                if self.settings.get('debugIsOn'):
                    self.debug_information("Spell checkbox not ticked")
                return False
    
        except Exception as e:
            self.output(f"Step {self.step} - Error during checkbox + continue sequence: {e}", 1)
            if self.settings.get('debugIsOn'):
                self.debug_information(f"Spell checkbox sequence error: {e}")
            return False

    def next_steps(self):
        if self.step:
            pass
        else:
            self.step = "01"

        try:
            self.launch_iframe()
            self.increase_step()

            self.spell_accept_and_continue()
            
            # Get balance
            balance_xpath = "//h2[contains(@class, 'chakra-heading css-1ougcld')]"
            self.get_balance(balance_xpath, False)

            # Final Housekeeping
            self.set_cookies()

        except TimeoutException:
            self.output(f"Step {self.step} - Failed to find or switch to the iframe within the timeout period.", 1)

        except Exception as e:
            self.output(f"Step {self.step} - An error occurred: {e}", 1)

    def full_claim(self):
        # Initialize status_text
        status_text = ""
        balance_xpath = "//div[contains(@class, 'css-6e4jug')]"

        # Launch iframe
        self.step = "100"
        self.launch_iframe()

        self.spell_accept_and_continue()

        # Capture the balance before the claim
        before_balance = self.get_balance(balance_xpath, False)

        # Pre-claim
        pre_claim = "//button[contains(normalize-space(.), 'Tap to claim') and contains(normalize-space(.), 'MANA')]"
        self.brute_click(pre_claim, 12, "click the pre 'Claim' button")
        self.increase_step()
        
        # Rapid-charge for ~10s (clicks ~4 times per second)
        if self.charge_until_complete(max_seconds=10, pause=0.25):
            self.output(f"Step {self.step} - Claim (Charging) sequence completed.", 3)
            self.increase_step()
        
            # Post-claim flow
            try:
                spin_xpath = "//p[contains(normalize-space(.), 'Spin the Wheel')]"
                self.move_and_click(spin_xpath, 10, True, "spin the wheel", self.step, "clickable")
            except Exception as e:
                self.output(f"Step {self.step} - Spin the wheel not available: {type(e).__name__}: {e}", 2)
            finally:
                self.increase_step()
        
            try:
                gotit_xpath = "//*[contains(normalize-space(text()), 'GOT IT')]"
                self.move_and_click(gotit_xpath, 10, True, "check for 'Got it' message (may not be present)", self.step, "clickable")
            except Exception as e:
                self.output(f"Step {self.step} - 'GOT IT' not shown (ok): {type(e).__name__}: {e}", 3)
            finally:
                self.increase_step()
        
            # Balance delta as you already do…
            after_balance = self.get_balance(balance_xpath, True)
            try:
                if before_balance is not None and after_balance is not None:
                    bal_diff = after_balance - before_balance
                    status_text += f"Claim submitted - balance increase {bal_diff:.2f} "
            except Exception as e:
                self.output(f"Step {self.step} - Error calculating balance difference: {e}", 1)
        else:
            self.output(f"Step {self.step} - Claim (Charging) did not complete in time.", 2)

        # Get the wait timer if present
        self.increase_step()
        remaining_wait_time = self.get_wait_time(self.step, "post-claim")
            
        # Do the Daily Puzzle from GitHub
        if self.daily_reward():
            status_text += "Daily Puzzle submitted"

        if not remaining_wait_time:
            self.output(f"STATUS: The wait timer is still showing: Filled.", 1)
            self.output(f"Step {self.step} - This means either the claim failed, or there is lag in the game.", 1)
            self.output(f"Step {self.step} - We'll check back in 1 hour to see if the claim processed and if not try again.", 2)
            return 60

        remaining_time = self.apply_random_offset(remaining_wait_time)
        
        # Output final status
        if status_text == "":
            self.output("STATUS: No claim or Daily Puzzle this time", 3)
        else:
            self.output(f"STATUS: {status_text}", 3)

        self.output(f"STATUS: Original wait time {remaining_wait_time} minutes, we'll sleep for {remaining_time} minutes after random offset.", 1)
        return max(remaining_time,60)

    def daily_reward(self):
        return
        # Switch to the Quests tab and check if Puzzle already solved
        xpath = "//p[contains(., 'Quests')]"
        success = self.move_and_click(xpath, 10, True, "click on 'Quests' tab", self.step, "clickable")
        self.increase_step()
        
        if not success:
            self.quit_driver()
            self.launch_iframe()
            self.move_and_click(xpath, 10, True, "click on 'Quests' tab", self.step, "clickable")
            self.increase_step()

        xpath = "//div[contains(@class, 'css-ehjmbb')]//p[contains(text(), 'Done')]"
        success = self.move_and_click(xpath, 10, True, "check if the puzzle has already been solved", self.step, "clickable")
        self.increase_step()
        if success:
            return False

        xpath = "//p[contains(., 'Daily Puzzle')]"
        self.move_and_click(xpath, 10, True, "click on 'Daily Puzzle' link", self.step, "clickable")
        self.increase_step()

        # Fetch the 4-digit code from the GitHub file using urllib
        url = "https://raw.githubusercontent.com/thebrumby/HotWalletClaimer/main/extras/rewardtest"
        try:
            with urllib.request.urlopen(url) as response:
                content = response.read().decode('utf-8').strip()
            self.output(f"Step {self.step} - Fetched code from GitHub: {content}", 3)
        except Exception as e:
            # Handle failure to fetch code
            self.output(f"Step {self.step} - Failed to fetch code from GitHub: {str(e)}", 2)
            return False

        self.increase_step()

        # Translate the numbers from GitHub to the symbols in the game
        for index, digit in enumerate(content):
            xpath = f"//div[@class='css-k0i5go'][{digit}]"
            
            if self.move_and_click(xpath, 30, True, f"click on the path corresponding to digit {digit}", self.step, "clickable"):
                self.output(f"Step {self.step} - Clicked on element corresponding to digit {digit}.", 2)
            else:
                # Handle failure to click on an element
                self.output(f"Step {self.step} - Element corresponding to digit {digit} not found or not clickable.", 1)

        self.increase_step()

        # Finish with some error checking
        invalid_puzzle_xpath = "//div[contains(text(), 'Invalid puzzle code')]/ancestor::div[contains(@class, 'chakra-alert')]"
        if self.move_and_click(invalid_puzzle_xpath, 30, True, "check if alert is present", self.step, "visible"):
            # Alert for invalid puzzle code is present
            self.output(f"Step {self.step} - Alert for invalid puzzle code is present.", 2)
        else:
            # Alert for invalid puzzle code is not present
            self.output(f"Step {self.step} - Alert for invalid puzzle code is not present.", 1)

        self.output(f"Step {self.step} - Completed daily reward sequence successfully.", 2)
        return True

    def get_wait_time(self, step_number="108", beforeAfter="pre-claim"):
        try:
            self.output(f"Step {self.step} - Get the wait time...", 3)
    
            # XPath to find the div element with the specific class
            xpath = "//div[@class='css-t9vhi1']"
            wait_time_text = self.monitor_element(xpath, 10, "claim timer")
    
            # Check if wait_time_text is not empty
            if wait_time_text:
                wait_time_text = wait_time_text.strip()
                self.output(f"Step {self.step} - Extracted wait time text: '{wait_time_text}'", 3)
    
                # Remove any spaces to standardize the format
                wait_time_text_clean = wait_time_text.replace(" ", "")
    
                # Regular expression to match patterns like '5h30m', '5h', '30m'
                pattern = r'(?:(\d+)h)?(?:(\d+)m)?'
                match = re.match(pattern, wait_time_text_clean)
    
                if match:
                    hours = match.group(1)
                    minutes = match.group(2)
                    total_minutes = 0
    
                    if hours:
                        total_minutes += int(hours) * 60
                    if minutes:
                        total_minutes += int(minutes)
    
                    self.output(f"Step {self.step} - Total wait time in minutes: {total_minutes}", 3)
                    return total_minutes if total_minutes > 0 else False
                else:
                    # If the pattern doesn't match, return False
                    self.output(f"Step {self.step} - Wait time pattern not matched in text: '{wait_time_text}'", 3)
                    return False
            else:
                # No text found in the element
                self.output(f"Step {self.step} - No wait time text found.", 3)
                return False
        except Exception as e:
            self.output(f"Step {self.step} - An error occurred: {e}", 3)
            return False

def main():
    claimer = SpellClaimer()
    claimer.run()

if __name__ == "__main__":
    main()
























