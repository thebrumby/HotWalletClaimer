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

from xnode import XNodeClaimer

class XNodeAUClaimer(XNodeClaimer):

    def initialize_settings(self):
        super().initialize_settings()
        self.script = "games/xnode-auto.py"
        self.prefix = "XNODE-Auto:"

    def __init__(self):
        super().__init__()
        self.start_app_xpath = "//div[contains(@class,'new-message-bot-commands-view')][contains(normalize-space(.),'Play')]"
        self.start_app_menu_item = "//a[.//span[contains(@class, 'peer-title') and normalize-space(text())='xNode: Core Protocol']]"
        
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

    def attempt_upgrade(self):
        self.output(f"Step {self.step} - Preparing to run the upgrader script - this may take some time.", 2)
        clicked = self.upgrade_all(max_passes=3, per_row_wait=6)
        if clicked > 0:
            return False
        return True
        
    def upgrade_all(self, max_passes=2, per_row_wait=4):
        """Click all upgrade rows that are actionable. 
           Skips rows that are disabled/unaffordable and only counts effective clicks."""
        from selenium.webdriver.common.by import By
        from selenium.webdriver.common.action_chains import ActionChains
        from selenium.common.exceptions import NoSuchElementException, StaleElementReferenceException, TimeoutException
    
        def class_has_token(el, token: str) -> bool:
            try:
                cls = (el.get_attribute("class") or "")
                return f" {token} " in f" {cls.strip()} "
            except StaleElementReferenceException:
                return True
    
        def aria_disabled(el) -> bool:
            try:
                v = (el.get_attribute("aria-disabled") or "").strip().lower()
                return v in ("1", "true", "yes")
            except StaleElementReferenceException:
                return True
    
        def style_blocks_click(el) -> bool:
            try:
                style = (el.get_attribute("style") or "").lower()
                # crude but useful: skip “pointer-events:none” or very low opacity
                if "pointer-events" in style and "none" in style:
                    return True
                # extract opacity value if present (opacity: 0.3; or inline opaque styles)
                import re
                m = re.search(r"opacity\s*:\s*([0-9.]+)", style)
                if m:
                    try:
                        return float(m.group(1)) < 0.5
                    except Exception:
                        return False
                return False
            except StaleElementReferenceException:
                return True
    
        def find_one(root, rel_xpaths):
            for xp in rel_xpaths:
                try:
                    el = root.find_element(By.XPATH, xp)
                    if el: 
                        return el
                except NoSuchElementException:
                    continue
                except StaleElementReferenceException:
                    return None
            return None
    
        def get_level_num(row):
            """Extract integer from 'Level: 21'."""
            try:
                lvl_el = row.find_element(By.XPATH, ".//h3[contains(@class,'Upgrader_text-lvl')]")
                txt = (lvl_el.text or "").strip()
                import re
                m = re.search(r"(\d+)", txt)
                return int(m.group(1)) if m else None
            except Exception:
                return None
    
        def row_is_effectively_disabled(row) -> bool:
            """Check row + controls for disabled semantics."""
            if class_has_token(row, "disable") or aria_disabled(row) or style_blocks_click(row):
                return True
            # check controls
            ctrl = find_one(row, [
                ".//div[contains(@class,'Upgrader_right-wrap')]",
                ".//div[contains(@class,'Upgrader_right')]",
                ".//div[contains(@class,'Upgrader_right-price_text')]",
            ])
            if ctrl is None:
                return True  # no control means nothing to click
            return class_has_token(ctrl, "disable") or aria_disabled(ctrl) or style_blocks_click(ctrl)
    
        def click_ctrl(ctrl, why=""):
            try:
                self.driver.execute_script("arguments[0].scrollIntoView({block:'center', inline:'center'});", ctrl)
                ActionChains(self.driver).move_to_element(ctrl).pause(0.05).click(ctrl).perform()
                return True
            except Exception:
                try:
                    self.driver.execute_script("arguments[0].click();", ctrl)
                    # self.output(f"Step {self.step} - JS click fallback for {why}.", 3)
                    return True
                except Exception:
                    return False
    
        container_xpath = "//div[contains(@class,'UpgradesPage-items')]"
        # exact token-safe match for NOT disabled at row-level (coarse prefilter)
        rows_xpath = (
            container_xpath +
            "//div[contains(@class,'Upgrader') and not(contains(concat(' ', normalize-space(@class), ' '), ' disable '))]"
        )
    
        targets = [
            ".//div[contains(@class,'Upgrader_right')]//div[contains(@class,'Upgrader_right-wrap')]",
            ".//div[contains(@class,'Upgrader_right-price_text')]",
            ".//div[contains(@class,'Upgrader_right')]",
        ]
    
        effective_clicks = 0
        self.output(f"Step {self.step} - Scanning Upgrader rows…", 2)
    
        for p in range(max_passes):
            acted = False
    
            # get snapshot; we’ll re-fetch inside the loop to avoid staleness
            snapshot = self.driver.find_elements(By.XPATH, rows_xpath)
            if not snapshot:
                self.output(f"Step {self.step} - No candidate rows found (pass {p+1}).", 3)
                break
    
            for idx in range(len(snapshot)):
                try:
                    # current view of this index
                    rows_now = self.driver.find_elements(By.XPATH, rows_xpath)
                    if idx >= len(rows_now):
                        continue
                    row = rows_now[idx]
    
                    # secondary strong disabled check
                    if row_is_effectively_disabled(row):
                        continue
    
                    # capture level before
                    lvl_before = get_level_num(row)
    
                    ctrl = find_one(row, targets)
                    if not ctrl:
                        continue
    
                    # first attempt
                    clicked = click_ctrl(ctrl, why=f"row {idx}")
                    if not clicked:
                        continue
    
                    acted = True
                    # brief settle
                    time.sleep(0.3)
    
                    # re-fetch row (may have moved); try to pick the same visual row again by title if needed
                    rows_after = self.driver.find_elements(By.XPATH, rows_xpath)
                    row2 = rows_after[idx] if idx < len(rows_after) else row
    
                    lvl_after = get_level_num(row2)
                    became_disabled = row_is_effectively_disabled(row2)
    
                    # if no effect, try once more
                    if (lvl_after is None or lvl_before is None or lvl_after == lvl_before) and not became_disabled:
                        ctrl2 = find_one(row2, targets)
                        if ctrl2:
                            click_ctrl(ctrl2, why=f"row {idx} (second)")
                            time.sleep(0.3)
                            rows_after2 = self.driver.find_elements(By.XPATH, rows_xpath)
                            row3 = rows_after2[idx] if idx < len(rows_after2) else row2
                            lvl_after2 = get_level_num(row3)
                            became_disabled = row_is_effectively_disabled(row3)
                            if (lvl_after2 is not None and lvl_before is not None and lvl_after2 > lvl_before) or became_disabled:
                                effective_clicks += 1
                            # else: no effect → don’t count
                        # else: no control → skip
                    else:
                        # we saw an effect after first click
                        effective_clicks += 1
    
                except StaleElementReferenceException:
                    continue
                except Exception as e:
                    # keep running even if one row explodes
                    self.output(f"Step {self.step} - Upgrader row {idx} error: {e}", 3)
                    continue
    
            if not acted:
                break  # nothing actionable this pass
    
            # optional: small pause between passes
            if per_row_wait:
                time.sleep(0.2)
    
        self.output(f"Step {self.step} - Upgrader loop finished. Effective upgrades: {effective_clicks}", 2)
        return effective_clicks

def main():
    claimer = XNodeAUClaimer()
    claimer.run()

if __name__ == "__main__":
    main()