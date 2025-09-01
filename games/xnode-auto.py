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
        """Prefer upgrading lowest-ROI rows first; count only effective upgrades.
           Includes full per-row debug of cost/gain/ROI & skip reasons.
        """
    
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
        # NOTE: include ALL rows for debugging; we'll decide enabled/disabled per row
        rows_xpath_all = container_xpath + "//div[contains(@class,'Upgrader')]"
    
        targets = [
            ".//div[contains(@class,'Upgrader_right')]//div[contains(@class,'Upgrader_right-wrap')]",
            ".//div[contains(@class,'Upgrader_right-price_text')]",
            ".//div[contains(@class,'Upgrader_right')]",
        ]
    
        effective_clicks = 0
        self.output(f"Step {self.step} - Scanning Upgrader rows by ROI (best first)…", 2)
    
        # single compute pass builds both debug + rank
        snapshot = self.driver.find_elements(By.XPATH, rows_xpath_all)
        if not snapshot:
            self.output(f"Step {self.step} - No Upgrader rows found at all.", 2)
            return 0
    
        MAX_ROI_SECS = 31 * 24 * 3600  # 31 days
    
        # Collect metrics for *every* row for debug
        all_rows_metrics = []
        for row in snapshot:
            try:
                title = get_title(row)
                lvl   = get_level_num(row)
                disabled = row_is_effectively_disabled(row)
                cost, gain = (0.0, 0.0)
                roi_sec = float("inf")
                parse_ok = True
                reason = ""
    
                try:
                    cost, gain = self._extract_cost_and_gain(row)
                    roi_sec = self._roi_seconds(cost, gain)
                except Exception as e:
                    parse_ok = False
                    reason = f"parse-failed: {type(e).__name__}"
    
                all_rows_metrics.append({
                    "title": title,
                    "level": lvl,
                    "disabled": disabled,
                    "cost": cost,
                    "gain": gain,
                    "roi_sec": roi_sec,
                    "parse_ok": parse_ok,
                    "skip_reason": reason
                })
            except Exception:
                continue
    
        # Emit debug for every row (cost/gain/ROI and reason if skipped)
        for m in all_rows_metrics:
            hrs = (m["roi_sec"] / 3600.0) if m["roi_sec"] not in (float("inf"), float("nan")) else float("inf")
            flags = []
            if m["disabled"]:
                flags.append("disabled")
            if not m["parse_ok"]:
                flags.append(m["skip_reason"] or "parse-failed")
            if m["roi_sec"] > MAX_ROI_SECS:
                flags.append(f"roi>{MAX_ROI_SECS}s")
            flag_txt = f" [{', '.join(flags)}]" if flags else ""
            self.output(
                f"Step {self.step} - ROI check: {m['title'] or 'Unknown'} (Lvl {m['level']}) → "
                f"Δ/sec={m['gain']:.3g}, Cost={m['cost']:.3g}, ROI≈{hrs:.2f}h{flag_txt}",
                3
            )
    
        # Build ranked list from metrics (enabled + within ROI cap + parsed ok)
        ranked = []
        for m in all_rows_metrics:
            if m["disabled"]:
                continue
            if not m["parse_ok"]:
                continue
            if m["roi_sec"] > MAX_ROI_SECS:
                continue
            # prefer lower ROI, then lower cost, then lower level, then title
            lvl_key = m["level"] if isinstance(m["level"], int) else 10**9
            ranked.append((m["roi_sec"], m["cost"], lvl_key, m["title"]))
    
        if not ranked:
            self.output(f"Step {self.step} - No actionable rows after ROI & state checks.", 2)
            return 0
    
        ranked.sort(key=lambda x: (x[0], x[1], x[2], x[3]))
    
        # Try upgrading in ROI order (multiple passes for resilience)
        for p in range(max_passes):
            acted = False
            for _, _, _, title in ranked:
                try:
                    row = find_row_by_title_exact(title)
                    if not row:
                        continue
                    if row_is_effectively_disabled(row):
                        continue
    
                    lvl_before = get_level_num(row)
                    ctrl = find_one(row, targets)
                    if not ctrl:
                        continue
    
                    if not click_ctrl(ctrl, why="upgrade click (1)"):
                        continue
    
                    acted = True
                    time.sleep(0.3)
    
                    row_fresh = find_row_by_title_exact(title) or row
                    lvl_after = get_level_num(row_fresh)
                    became_disabled = row_is_effectively_disabled(row_fresh)
    
                    success = False
                    if (lvl_after is None or lvl_before is None or lvl_after == lvl_before) and not became_disabled:
                        ctrl2 = find_one(row_fresh, targets) or find_one(row, targets)
                        if ctrl2 and click_ctrl(ctrl2, why="upgrade click (2)"):
                            time.sleep(0.3)
                            row_fresh2 = find_row_by_title_exact(title) or row_fresh
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
                        lvl_print = (
                            f"{(lvl_before or 0) + 1}" if (lvl_after is None and isinstance(lvl_before, int))
                            else (f"{lvl_after}" if isinstance(lvl_after, int)
                                  else (f"{lvl_before}" if isinstance(lvl_before, int) else "?"))
                        )
                        self.output(f"Step {self.step} - Upgraded {title} at level {lvl_print}", 3)
    
                except StaleElementReferenceException:
                    continue
                except Exception as e:
                    self.output(f"Step {self.step} - Upgrader row error ({title}): {e}", 3)
                    continue
    
            if not acted:
                break
            if per_row_wait:
                time.sleep(0.2)
    
        self.output(f"Step {self.step} - Upgrader loop finished. Effective upgrades: {effective_clicks}", 2)
        return effective_clicks
        
    # --- helpers (fixed) ---
    import re
    UNIT = {"K":1e3, "M":1e6, "B":1e9, "T":1e12, "P":1e15}
    
    def _parse_qty(self, text: str) -> float:
        """
        Accept '400.6M', '1.2B', '+260', '150B tflops/sec', spaces, non-breaking spaces, etc.
        Returns a float in base units (tflops or tflops/sec).
        """
        if text is None:
            return 0.0
        t = str(text).replace("\xa0", " ").strip()  # NBSP -> space
        if not t:
            return 0.0
        t = t.replace(" ", "")                       # remove spaces entirely
        # keep leading sign/number/decimal, capture trailing unit letters (1–2 chars)
        # e.g. "400.6M", "1.2B", "+260", "150Btf/s"
        m = re.match(r'^([+-]?\d+(?:\.\d+)?)([A-Za-z]{0,2}).*$', t)
        if not m:
            return 0.0
        num = float(m.group(1))
        suf = (m.group(2) or "").upper()
        if suf in UNIT:
            return num * UNIT[suf]
        return num
    
    def _extract_cost_and_gain(self, row):
        # ----- COST -----
        price_el = row.find_element(By.XPATH, ".//div[contains(@class,'Upgrader_right-price_text')]")
        price_txt = (price_el.text or "").strip()
        if not price_txt:
            price_txt = (self.driver.execute_script("return arguments[0].textContent;", price_el) or "").strip()
        # helpful debug
        self.output(f"Step {self.step} - raw cost text: '{price_txt}'", 3)
        cost = self._parse_qty(price_txt)
    
        # ----- GAIN (Income delta per sec) -----
        gain_el = row.find_element(By.XPATH, ".//div[contains(@class,'Upgrader_income')]/span[2]")
        gain_txt = (gain_el.text or "").strip()
        if not gain_txt:
            gain_txt = (self.driver.execute_script("return arguments[0].textContent;", gain_el) or "").strip()
        self.output(f"Step {self.step} - raw gain text: '{gain_txt}'", 3)
        gain = self._parse_qty(gain_txt)
    
        return cost, gain
    
    def _roi_seconds(self, cost, gain):
        if not gain or gain <= 0:
            return float("inf")
        return cost / gain

def main():
    claimer = XNodeAUClaimer()
    claimer.run()

if __name__ == "__main__":

    main()





