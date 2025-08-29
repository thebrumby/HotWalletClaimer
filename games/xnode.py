import os
import shutil
import sys
import time
import re
import json
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

class XNodeClaimer(Claimer):

    def initialize_settings(self):
        super().initialize_settings()
        self.script = "games/xnode.py"
        self.prefix = "XNODE:"
        self.url = "https://web.telegram.org/k/#@xnode_bot"
        self.pot_full = "Filled"
        self.pot_filling = "to fill"
        self.seed_phrase = None
        self.forceLocalProxy = False
        self.forceRequestUserAgent = False
        self.step = "01"
        self.imported_seedphrase = None
        self.start_app_xpath = "//div[contains(@class,'new-message-bot-commands-view')][contains(normalize-space(.),'Play')]"
        self.start_app_menu_item = "//a[.//span[contains(@class, 'peer-title') and normalize-space(text())='xNode: Core Protocol']]"

    def __init__(self):
        self.settings_file = "variables.txt"
        self.status_file_path = "status.txt"
        self.wallet_id = ""
        self.load_settings()
        self.random_offset = random.randint(self.settings['lowestClaimOffset'], self.settings['highestClaimOffset'])
        super().__init__()
        
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
            self.output(f"Step {self.step} - Failed to find or switch to the iframe within the timeout period.",1)

        except Exception as e:
            self.output(f"Step {self.step} - An error occurred: {e}",1)
    
    def full_claim(self):
        self.step = "100"
    
        self.launch_iframe()
    
        xpath = "//button[normalize-space(text())='skip']"
        self.move_and_click(xpath, 10, True, "skip the introduction screens (may not be present)", self.step, "clickable")
        self.increase_step()
    
        xpath = "//button[normalize-space(text())='claim']"
        self.move_and_click(xpath, 10, True, "claim the daily reward (may not be present)", self.step, "clickable")
        self.increase_step()
    
        xpath = "//div[@data-title='XNode CPU']//canvas"
        self.move_and_click(xpath, 10, True, "tap the chip (may not be present)", self.step, "clickable")
        self.increase_step()
    
        xpath = "//button[normalize-space()='собрать']"
        self.move_and_click(xpath, 10, True, "collect the TFlops (may not be present)", self.step, "clickable")
        self.increase_step()
    
        balance_xpath = "//span[normalize-space(.)='XPoints']/preceding-sibling::span[1]"
        self.get_balance(balance_xpath, False)
        self.increase_step()      
    
        # Grab the wait time 
        wait_xpath = "//div[@class='TimeTracker']//span[contains(@class,'TimeTracker_text')]"
        action, minutes = self.decide_wait_or_claim(wait_xpath, label="pre-claim", respect_force=True)
        
        # Then run the upgrader
        self.get_profit_hour(False)
        skip = self.attempt_upgrade()        
        
        # First decision: wait or claim now
        if action == "sleep":
            return minutes
         
        # If the upgrader ran, reload the UI.    
        if not skip:
            self.quit_driver()
            self.launch_iframe()
            self.get_profit_hour(True)
    
        # Proceed to (re)start mining / claim sequence
        checkbox_wrap_xpath = ("//div[contains(@class,'AutoFarmChecker')]"
                               "//div[contains(@class,'CheckBox')]/div[contains(@class,'CheckBox_wrapper')]")
        
        if not self.is_autofarm_active():
            # nice to log:
            self.output(f"Step {self.step} - AutoFarm is OFF; toggling ON…", 2)
        
            def became_active():
                return self.is_autofarm_active()
        
            # use your brute_click as a fallback; otherwise move_and_click works too
            ok = self.brute_click(checkbox_wrap_xpath, timeout=5,
                                  action_description="toggle AutoFarm", state_check=became_active)
            if not ok and not self.is_autofarm_active():
                # one more direct JS center click if needed
                try:
                    el = self.driver.find_element(By.XPATH, checkbox_wrap_xpath)
                    self.driver.execute_script("""
                        const el = arguments[0];
                        const r = el.getBoundingClientRect();
                        const x = r.left + r.width/2, y = r.top + r.height/2;
                        for (const t of ['pointerdown','mousedown','pointerup','mouseup','click']) {
                          el.dispatchEvent(new MouseEvent(t,{bubbles:true,cancelable:true,clientX:x,clientY:y}));
                        }
                    """, el)
                except Exception:
                    pass
        
            self.output(f"Step {self.step} - AutoFarm active? {self.is_autofarm_active()}", 3)
        else:
            self.output(f"Step {self.step} - AutoFarm already ON; no click needed.", 3)
    
        # Second decision after the click
        action2, minutes2 = self.decide_wait_or_claim(wait_xpath, label="post-restart", respect_force=False)
        if action2 == "sleep":
            return minutes2
    
        # If we still can’t get a positive wait, be safe and try again in an hour
        return 60
        
    def autofarm_checkbox_root(self):
        return self.driver.find_element(By.XPATH,
            "//div[contains(@class,'AutoFarmChecker')]//div[contains(@class,'CheckBox')]"
        )
    
    def is_autofarm_active(self):
        try:
            root = self.autofarm_checkbox_root()
            cls = " " + (root.get_attribute("class") or "") + " "
            return " active " in cls
        except Exception:
            return False
    
    def decide_wait_or_claim(self, wait_xpath, label="pre-claim", respect_force=True):
        mins = self.get_wait_time(wait_xpath, timeout=12, label=label)
        self.increase_step()

        if mins is False:
            self.output(f"Step {self.step} - Wait time unavailable; defaulting to 60 minutes.", 2)
            return ("sleep", 60)

        remaining = float(mins)
        threshold = abs(self.settings['lowestClaimOffset']) if self.settings['lowestClaimOffset'] < 0 else 5

        # sleep only if we're allowed to ignore forceClaim or it's not set
        if remaining > threshold and not (respect_force and self.settings.get("forceClaim")):
            sleep_minutes = self.apply_random_offset(remaining)
            self.output(f"STATUS: {label} wait {remaining} min (> {threshold}); "
                        f"sleeping {sleep_minutes} min after random offset.", 1)
            return ("sleep", sleep_minutes)

        # claim now
        if respect_force:
            self.settings['forceClaim'] = True
        self.output(f"Step {self.step} - {label}: remaining {remaining}m ≤ threshold {threshold}m "
                    f"or forceClaim set; proceeding to claim.", 3)
        return ("claim", 0)
            
    def get_wait_time(self, wait_time_xpath, timeout=12, label="wait timer"):
        import re
    
        def _read_text():
            # Try monitor first
            t = self.monitor_element(wait_time_xpath, timeout, label)
            if t and not isinstance(t, bool) and str(t).strip():
                return str(t)
            # Fallback: DOM textContent
            try:
                els = self.driver.find_elements(By.XPATH, wait_time_xpath)
                for el in els:
                    t = self.driver.execute_script("return arguments[0].textContent;", el)
                    if t and str(t).strip():
                        return str(t)
            except Exception:
                pass
            return ""
    
        try:
            self.output(f"Step {self.step} - Get the wait time...", 3)
    
            raw = _read_text()
            if not raw:
                self.output(f"Step {self.step} - No wait time text found.", 3)
                return False

            # normalise
            text = " ".join(raw.split()).replace(",", ".")
            txt = text.lower()
            self.output(f"Step {self.step} - Extracted wait time text: '{text}'", 3)

            total_minutes = 0.0
            found_any = False

            # A) tokenised formats like "7.8h", "1h 30m", "540s", "1d 2h"
            for mult, pat in [
                (1440.0, r'(\d+(?:\.\d+)?)\s*d'),
                (  60.0, r'(\d+(?:\.\d+)?)\s*h'),
                (   1.0, r'(\d+(?:\.\d+)?)\s*m(?!s)'),
                (1/60.0, r'(\d+(?:\.\d+)?)\s*s\b'),
            ]:
                for m in re.findall(pat, txt, flags=re.I):
                    try:
                        total_minutes += float(m) * mult
                        found_any = True
                    except Exception:
                        pass

            # B) HH:MM[:SS] if no unit tokens were found
            if not found_any:
                m = re.search(r'\b(\d{1,2}):(\d{2})(?::(\d{2}))?\b', txt)
                if m:
                    h  = int(m.group(1) or 0)
                    mn = int(m.group(2) or 0)
                    s  = int(m.group(3) or 0)
                    total_minutes = h * 60 + mn + s / 60.0
                    found_any = True

            # ✅ accept zero minutes as valid
            if found_any:
                total_minutes = max(0.0, round(total_minutes, 1))
                self.output(f"Step {self.step} - Total wait time in minutes: {total_minutes}", 3)
                return total_minutes

            self.output(f"Step {self.step} - Wait time pattern not matched in text: '{text}'", 3)
            return False
    
        except Exception as e:
            self.output(f"Step {self.step} - An error occurred in get_wait_time: {type(e).__name__}: {e}", 3)
            return False
            
    def get_profit_hour(self, claimed=False):
        prefix = "After" if claimed else "Before"
        default_priority = 2 if claimed else 3
        priority = max(self.settings['verboseLevel'], default_priority)
    
        profit_xpath = "//div[contains(@class,'ItemGrout_subChildren')]//span[contains(text(),'/sec')]"
    
        try:
            text = self.monitor_element(profit_xpath, 15, "profit per sec")
            if not text or isinstance(text, bool):
                self.output(f"Step {self.step} - Could not find profit text.", priority)
                return False
    
            raw = text.strip()
            self.output(f"Step {self.step} - Raw profit string: '{raw}'", 3)
    
            # Extract number before "/sec"
            import re
            m = re.search(r'([+-]?\d+(?:\.\d+)?)\s*/sec', raw, flags=re.I)
            if not m:
                self.output(f"Step {self.step} - Profit pattern not matched in '{raw}'.", priority)
                return False
    
            per_sec = float(m.group(1))
            per_hour = round(per_sec * 3600, 2)
    
            self.output(f"Step {self.step} - {prefix} PROFIT/HOUR: {per_hour}", priority)
            return per_hour
    
        except NoSuchElementException:
            self.output(f"Step {self.step} - Profit element not found.", priority)
            return False
        except Exception as e:
            self.output(f"Step {self.step} - Error in get_profit_hour: {e}", priority)
            return False
        finally:
            self.increase_step()
            
    def attempt_upgrade(self):
        # skip if it's not the auto-upgrade version
        return True

def main():
    claimer = XNodeClaimer()
    claimer.run()

if __name__ == "__main__":
    main()


