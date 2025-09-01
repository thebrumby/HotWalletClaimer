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
        """Prefer upgrading lowest-ROI rows first; count only effective upgrades."""
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
                if "pointer-events" in style and "none" in style:
                    return True
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
    
        def get_title(row):
            try:
                t = row.find_element(By.XPATH, ".//h2[contains(@class,'Upgrader_text-title')]")
                txt = (t.text or "").strip()
                if not txt:
                    txt = (self.driver.execute_script("return arguments[0].textContent;", t) or "").strip()
                return txt
            except Exception:
                return ""
    
        def get_level_num(row):
            try:
                lvl_el = row.find_element(By.XPATH, ".//h3[contains(@class,'Upgrader_text-lvl')]")
                txt = (lvl_el.text or "").strip()
                if not txt:
                    txt = (self.driver.execute_script("return arguments[0].textContent;", lvl_el) or "").strip()
                m = re.search(r"(\d+)", txt)
                return int(m.group(1)) if m else None
            except Exception:
                return None
    
        def find_row_by_title_exact(title):
            try:
                # Safe literal for XPath
                if "'" in title and '"' in title:
                    parts = title.split("'")
                    xp_lit = "concat(" + ", \"'\", ".join([f"'{p}'" for p in parts]) + ")"
                elif "'" in title:
                    xp_lit = f'"{title}"'
                else:
                    xp_lit = f"'{title}'"
                xp = ("//div[contains(@class,'Upgrader')]"
                      f"[.//h2[contains(@class,'Upgrader_text-title') and normalize-space()={xp_lit}]]")
                return self.driver.find_element(By.XPATH, xp)
            except Exception:
                return None
    
        def row_is_effectively_disabled(row) -> bool:
            if class_has_token(row, "disable") or aria_disabled(row) or style_blocks_click(row):
                return True
            ctrl = find_one(row, [
                ".//div[contains(@class,'Upgrader_right-wrap')]",
                ".//div[contains(@class,'Upgrader_right')]",
                ".//div[contains(@class,'Upgrader_right-price_text')]",
            ])
            if ctrl is None:
                return True
            return class_has_token(ctrl, "disable") or aria_disabled(ctrl) or style_blocks_click(ctrl)
    
        def click_ctrl(ctrl, why=""):
            try:
                self.driver.execute_script("arguments[0].scrollIntoView({block:'center', inline:'center'});", ctrl)
                ActionChains(self.driver).move_to_element(ctrl).pause(0.05).click(ctrl).perform()
                return True
            except Exception:
                try:
                    self.driver.execute_script("arguments[0].click();", ctrl)
                    return True
                except Exception:
                    return False
    
        container_xpath = "//div[contains(@class,'UpgradesPage-items')]"
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
        self.output(f"Step {self.step} - Scanning Upgrader rows by ROI (best first)…", 2)
    
        for p in range(max_passes):
            acted = False
    
            snapshot = self.driver.find_elements(By.XPATH, rows_xpath)
            if not snapshot:
                self.output(f"Step {self.step} - No candidate rows found (pass {p+1}).", 3)
                break
    
            # Build ranking list
            ranked = []
            for row in snapshot:
                try:
                    if row_is_effectively_disabled(row):
                        continue
                    cost, gain = self._extract_cost_and_gain(row)   # ← use self.
                    roi_sec = self._roi_seconds(cost, gain)
                    lvl = get_level_num(row)
                    title = get_title(row)
                    lvl_key = lvl if isinstance(lvl, int) else 10**9
                    ranked.append((roi_sec, cost, lvl_key, title, row))
    
                    if self.settings.get('verboseLevel', 2) >= 3:
                        hrs = (roi_sec / 3600.0) if roi_sec != float('inf') else float('inf')
                        self.output(
                            f"Step {self.step} - ROI est: {title} → {hrs:.2f}h (Δ/sec={gain:.3g}, Cost={cost:.3g})",
                            3
                        )
                except StaleElementReferenceException:
                    continue
                except Exception:
                    continue
    
            # Optional ROI cap (e.g., ignore >10 days)
            MAX_ROI_SECS = 10 * 24 * 3600
            ranked = [t for t in ranked if t[0] <= MAX_ROI_SECS]
    
            # Sort by ROI asc, then lower cost, then lower level, then title
            ranked.sort(key=lambda x: (x[0], x[1], x[2], x[3]))
    
            if not ranked:
                self.output(f"Step {self.step} - No actionable rows this pass.", 3)
                break
    
            for _, _, _, _, row in ranked:
                try:
                    if row_is_effectively_disabled(row):
                        continue
    
                    title_before = get_title(row)
                    lvl_before   = get_level_num(row)
    
                    ctrl = find_one(row, targets)
                    if not ctrl:
                        continue
    
                    if not click_ctrl(ctrl, why="upgrade click (1)"):
                        continue
    
                    acted = True
                    time.sleep(0.3)
    
                    row_fresh = find_row_by_title_exact(title_before) or row
                    lvl_after = get_level_num(row_fresh)
                    became_disabled = row_is_effectively_disabled(row_fresh)
    
                    success = False
                    if (lvl_after is None or lvl_before is None or lvl_after == lvl_before) and not became_disabled:
                        ctrl2 = find_one(row_fresh, targets) or find_one(row, targets)
                        if ctrl2 and click_ctrl(ctrl2, why="upgrade click (2)"):
                            time.sleep(0.3)
                            row_fresh2 = find_row_by_title_exact(title_before) or row_fresh
                            lvl_after2 = get_level_num(row_fresh2)
                            became_disabled = row_is_effectively_disabled(row_fresh2)
                            success = ((lvl_after2 is not None and lvl_before is not None and lvl_after2 > lvl_before)
                                       or became_disabled)
                            if success:
                                lvl_after = lvl_after2
                    else:
                        success = True
    
                    if success:
                        effective_clicks += 1
                        if lvl_after is None and isinstance(lvl_before, int):
                            lvl_print = f"{lvl_before + 1}"
                        elif isinstance(lvl_after, int):
                            lvl_print = f"{lvl_after}"
                        elif isinstance(lvl_before, int):
                            lvl_print = f"{lvl_before}"
                        else:
                            lvl_print = "?"
                        title_print = title_before or get_title(row_fresh) or "Unknown upgrade"
                        self.output(f"Step {self.step} - Upgraded {title_print} at level {lvl_print}", 3)
    
                except StaleElementReferenceException:
                    continue
                except Exception as e:
                    self.output(f"Step {self.step} - Upgrader row error: {e}", 3)
                    continue
    
            if not acted:
                break
            if per_row_wait:
                time.sleep(0.2)
    
        self.output(f"Step {self.step} - Upgrader loop finished. Effective upgrades: {effective_clicks}", 2)
        return effective_clicks
        
    # --- helpers ---
    UNIT = {"K":1e3,"M":1e6,"B":1e9,"T":1e12,"P":1e15}
    
    def _parse_qty(text: str) -> float:
        # Accept forms like: "759.6M", "1T", "2.1P", "1 200 M" etc.
        t = (text or "").replace("\xa0"," ").strip()
        t = t.replace(" ", "")  # squish
        if not t:
            return 0.0
        # split number + optional suffix
        num = ""
        suf = ""
        for ch in t:
            if ch.isdigit() or ch in ".-+":
                num += ch
            else:
                suf += ch
        try:
            q = float(num)
        except:
            return 0.0
        suf = (suf or "").upper()
        # tolerate trailing words like "TFLOPS" "TFLOPS/SEC"
        for k in ("K","M","B","T","P"):
            if suf.startswith(k):
                return q * UNIT[k]
        # no recognized suffix → plain number
        return q
    
    def _extract_cost_and_gain(row):
        # cost: right price text
        price_el = row.find_element(By.XPATH, ".//div[contains(@class,'Upgrader_right-price_text')]")
        price_txt = price_el.text  # e.g. "759.6M tflops"
        cost = _parse_qty(price_txt)
    
        # gain: “Income: +XYZ <unit> tflops/sec” -> the middle span
        gain_el = row.find_element(By.XPATH, ".//div[contains(@class,'Upgrader_income')]/span[2]")
        gain_txt = gain_el.text  # e.g. "+10M"
        gain = _parse_qty(gain_txt)
    
        return cost, gain
    
    def _roi_seconds(cost, gain):
        # Protect against zero/None
        if not gain or gain <= 0:
            return float("inf")
        return cost / gain

def main():
    claimer = XNodeAUClaimer()
    claimer.run()

if __name__ == "__main__":

    main()




