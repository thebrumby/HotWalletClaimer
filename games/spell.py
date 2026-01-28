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
from claimer_improved import Claimer

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
        checkbox_xpath = "//span[@aria-hidden='true' and contains(@class,'chakra-checkbox__control')]"
        btn_xpath      = "//button[contains(@class,'chakra-button') and normalize-space()='Get Started']"
    
        try:
            # Look for checkbox without throwing (0/1 elements)
            boxes = self.driver.find_elements(By.XPATH, checkbox_xpath)
            if not boxes:
                # Checkbox already gone → proceed
                self.output(f"Step {self.step} - Checkbox not present; assuming already accepted. Proceeding.", 2)
                try:
                    btns = self.driver.find_elements(By.XPATH, btn_xpath)
                    if btns:
                        self.driver.execute_script("arguments[0].click();", btns[0])
                        self.output(f"Step {self.step} - Clicked 'Get Started'.", 2)
                except Exception:
                    pass
                return True
    
            checkbox = boxes[0]
    
            # Scroll into view and synthesize a real click
            self.driver.execute_script("""
                const el = arguments[0];
                el.scrollIntoView({block:'center', inline:'center'});
                const r = el.getBoundingClientRect();
                const x = r.left + r.width/2, y = r.top + r.height/2;
                for (const t of ['pointerdown','mousedown','mouseup','click']) {
                  el.dispatchEvent(new MouseEvent(t, {bubbles:true, cancelable:true, clientX:x, clientY:y}));
                }
            """, checkbox)
            time.sleep(0.5)
    
            # Verify toggle (or just continue if button becomes enabled)
            if checkbox.get_attribute("data-checked") is not None:
                self.output(f"Step {self.step} - Checkbox ticked successfully.", 2)
            else:
                self.output(f"Step {self.step} - Checkbox did not report data-checked; proceeding anyway.", 2)
    
            # Try to click "Get Started" if present
            btns = self.driver.find_elements(By.XPATH, btn_xpath)
            if btns:
                self.driver.execute_script("arguments[0].click();", btns[0])
                self.output(f"Step {self.step} - Clicked 'Get Started'.", 2)
            else:
                self.output(f"Step {self.step} - 'Get Started' button not present (ok).", 3)
    
            return True
    
        except Exception as e:
            # Graceful fallback: don't fail the flow if this UI already passed
            self.output(f"Step {self.step} - Checkbox/continue sequence: {type(e).__name__}: {e}. Proceeding.", 2)
            if self.settings.get('debugIsOn'):
                self.debug_information(f"Spell checkbox sequence (non-fatal): {e}")
            return True

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

        # Get the wait timer if present
        self.increase_step()
        remaining_wait_time = self.get_wait_time(self.step, "post-claim")
            
        # Get the wait timer if present
        self.increase_step()
        pre_wait_min = self.get_wait_time(before_after="pre-claim")

        if pre_wait_min > 0:
            # Respect the timer and bail early
            wait_with_jitter = self.apply_random_offset(pre_wait_min)
            self.output(
                f"STATUS: Original wait time {pre_wait_min} minutes, we'll sleep for "
                f"{wait_with_jitter} minutes after random offset.", 1
            )
            return max(wait_with_jitter, 60)
            
        # Pre-claim
        pre_claim = "//button[contains(normalize-space(.), 'Tap to claim') and contains(normalize-space(.), 'MANA')]"
        self.brute_click(pre_claim, 12, "click the pre 'Claim' button")
        self.increase_step()
        
        # Rapid-charge for ~10s (clicks ~4 times per second)
        self.charge_until_complete(max_seconds=10, pause=0.25)
        self.increase_step()
        
        # Reload the browser after claim
        self.quit_driver()
        self.launch_driver()
            
        # Balance is not already taken due to output priority
        if not before_balance:
            after_balance = self.get_balance(balance_xpath, True)
        
        # Get the wait timer if present
        self.increase_step()
        post_wait_min = self.get_wait_time(before_after="post-claim")  # correct call

        # Daily puzzle (optional)
        if self.daily_reward():
            status_text += "Daily Puzzle submitted"

        # If timer missing or zero, assume lag / retry later
        if not post_wait_min:
            self.output("STATUS: The wait timer is still showing: Filled.", 1)
            self.output("Step {self.step} - This means either the claim failed, or there is lag in the game.", 1)
            self.output("Step {self.step} - We'll check back in 1 hour to see if the claim processed and if not try again.", 2)
            return 60

        wait_with_jitter = self.apply_random_offset(post_wait_min)
        if status_text == "":
            self.output("STATUS: No claim or Daily Puzzle this time", 3)
        else:
            self.output(f"STATUS: {status_text}", 3)

        self.output(
            f"STATUS: Original wait time {post_wait_min} minutes, we'll sleep for "
            f"{wait_with_jitter} minutes after random offset.", 1
        )
        return max(wait_with_jitter, 60)

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

    def get_wait_time(self, before_after="pre-claim", timeout=10):
        """
        Reads a timer like '5h 47m' from the UI and returns total minutes (int).
        If the element is missing or text doesn't match, returns 0.
        """
        try:
            self.output(f"Step {self.step} - Get the wait time ({before_after})...", 3)

            # coerce timeout safely
            try:
                to = float(timeout)
            except Exception:
                to = 10.0  # sensible default

            xpath = "//div[contains(@class,'css-lwfv40')]"
            wait_time_text = self.monitor_element(xpath, to, "claim timer")

            if not wait_time_text or isinstance(wait_time_text, bool):
                self.output(f"Step {self.step} - No wait time element/text found; assuming 0m.", 3)
                return 0

            raw = str(wait_time_text).strip()
            self.output(f"Step {self.step} - Extracted wait time text: '{raw}'", 3)

            # Accept '5h 47m', '5h', '47m', allowing extra spaces/case
            m = re.fullmatch(r'\s*(?:(\d+)\s*h)?\s*(?:(\d+)\s*m)?\s*', raw, flags=re.I)
            if not m:
                self.output(f"Step {self.step} - Wait time pattern not matched in text: '{raw}'. Assuming 0m.", 3)
                return 0

            hours = int(m.group(1) or 0)
            minutes = int(m.group(2) or 0)
            total_minutes = hours * 60 + minutes

            self.output(f"Step {self.step} - Total wait time in minutes: {total_minutes}", 3)
            return total_minutes

        except Exception as e:
            self.output(f"Step {self.step} - Error while parsing wait time: {e}. Assuming 0m.", 3)
            return 0

def main():
    claimer = SpellClaimer()
    claimer.run()

if __name__ == "__main__":
    main()































