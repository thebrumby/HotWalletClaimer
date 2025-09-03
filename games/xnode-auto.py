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

# ---------- module-level constants ----------
MAX_ROI_DAYS = 31
MAX_ROI_SEC  = MAX_ROI_DAYS * 24 * 3600

UNIT = {"K":1e3, "M":1e6, "B":1e9, "T":1e12, "P":1e15}
# -------------------------------------------

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
        
    # ---- tiny helpers (put these inside your class, above upgrade_all) ----
    def _in_game_dom(self) -> bool:
        try:
            if self.driver.find_elements(By.XPATH, "//div[contains(@class,'Upgrader')]"):
                return True
            if self.driver.find_elements(By.XPATH, "//div[contains(@class,'UpgradesPage')]"):
                return True
            return False
        except Exception:
            return False
    
    def _hrs_str(self, seconds):
        import math
        return "∞h" if not math.isfinite(seconds) else f"{seconds/3600.0:.2f}h"
    
    # ---- drop-in replacement for upgrade_all ----
    def upgrade_all(self, max_passes=2, per_row_wait=4):
        """Scan upgrades, compute ROI/TTA/ETA, and upgrade in best-first order.
           Uses persisted self.profit_per_sec from Step 114 when available.
        """
    
        # ---------- Tunables ----------
        USE_ETA_PLANNING = True           # True = choose best ETA (wait allowed); False = pure ROI-first now
        ETA_DECISION_MARGIN_SEC = 0       # Require disabled best ETA to beat best affordable ROI by this many seconds
        # -------------------------------
    
        import math, re, time
        from selenium.common.exceptions import NoSuchElementException, StaleElementReferenceException
    
        # --- 0) Enter iframe only if not already in game DOM ---
        if not self._in_game_dom():
            self.output(f"Step {self.step} - Not in game DOM; attempting to enter iframe…", 3)
            try:
                self.launch_iframe()
            except Exception as e:
                self.output(f"Step {self.step} - launch_iframe() failed: {e}", 2)
    
        # --- helpers local to this method ---
        def _norm(s: str) -> str:
            return (s or "").replace("\xa0", " ").strip()
    
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
                    return float(m.group(1)) < 0.5
                return False
            except StaleElementReferenceException:
                return True
    
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
    
        # --- 1) Wait & collect rows (lenient, with fallbacks) ---
        WebDriverWait(self.driver, 10).until(
            EC.presence_of_element_located((
                By.XPATH,
                "//div[contains(@class,'UpgradesPage-items')]"
                " | //div[contains(@class,'Upgrader') and .//h2[contains(@class,'Upgrader_text-title')]]"
            ))
        )
    
        all_containers = self.driver.find_elements(By.XPATH, "//div[contains(@class,'UpgradesPage-items')]")
        containers = [c for c in all_containers if getattr(c, 'is_displayed', lambda: True)()]
        if not containers:
            containers = all_containers[:]
        if not containers:
            containers = [self.driver]  # search whole document
    
        row_xpath_core = (
            ".//div[contains(@class,'Upgrader') and "
            " .//h2[contains(@class,'Upgrader_text-title')] and "
            " .//div[contains(@class,'Upgrader_right-price_text')] ]"
        )
        row_xpath_fallback = (
            ".//div[contains(@class,'Upgrader') and "
            " .//h2[contains(@class,'Upgrader_text-title')] ]"
        )
    
        rows = []
        for cont in containers:
            try:
                rows.extend(cont.find_elements(By.XPATH, row_xpath_core))
            except Exception:
                pass
        if not rows:
            for cont in containers:
                try:
                    rows.extend(cont.find_elements(By.XPATH, row_xpath_fallback))
                except Exception:
                    pass
    
        snapshot = rows
        self.output(
            f"Step {self.step} - Upgrade Categories: {len(all_containers)} | Total Upgrades: {len(snapshot)}",
            3
        )
       
        if not snapshot:
            time.sleep(0.6)  # one-shot tiny retry
            rows = []
            for cont in containers:
                try:
                    rows.extend(cont.find_elements(By.XPATH, row_xpath_core))
                except Exception:
                    pass
            if not rows:
                for cont in containers:
                    try:
                        rows.extend(cont.find_elements(By.XPATH, row_xpath_fallback))
                    except Exception:
                        pass
            snapshot = rows
    
        if not snapshot:
            self.output(f"Step {self.step} - No Upgrader rows found (after fallback retry). Holding.", 2)
            return 0
    
        # --- 1a) Get profit/sec and balance ---
        # Prefer persisted profit/sec from Step 114
        try:
            profit_per_sec = float(getattr(self, "profit_per_sec", 0.0))
        except Exception:
            profit_per_sec = 0.0
    
        def _parse_profit_per_sec_fallback():
            try:
                el = self.driver.find_element(By.XPATH, "//*[contains(text(),'/SEC') or contains(text(),'/sec')]")
                raw = _norm(el.text or self.driver.execute_script("return arguments[0].textContent;", el) or "")
                m = re.search(r'([+-]?\d+(?:\.\d+)?\s*[KMBTP]?)\s*/\s*SEC', raw, re.I)
                if m:
                    return self._parse_qty(m.group(1))
            except Exception:
                pass
            return 0.0
    
        if profit_per_sec <= 0:
            profit_per_sec = _parse_profit_per_sec_fallback()
    
        def _parse_current_balance():
            try:
                el = self.driver.find_element(By.XPATH, "//*[contains(@class,'balance') or contains(text(),'tflops')]")
                raw = _norm(el.text or self.driver.execute_script("return arguments[0].textContent;", el) or "")
                m = re.search(r'([+-]?\d+(?:\.\d+)?\s*[KMBTP]?)\s*(?:tflops|TFLOPS)?', raw, re.I)
                if m:
                    return self._parse_qty(m.group(1))
            except Exception:
                pass
            return 0.0
    
        current_balance = _parse_current_balance()
    
        # --- 2) Scan → metrics (ROI/TTA/ETA), de-dup, partition ---
        seen = set()
        all_rows_metrics = []
        actionable_now = []
        disabled_considered = []
        
        for row in snapshot:
            title = ""
            try:
                try:
                    self.driver.execute_script(
                        "arguments[0].scrollIntoView({block:'center', inline:'nearest'});", row
                    )
                except Exception:
                    pass
        
                title = _norm(get_title(row))
                if not title:
                    m = {
                        "title": "", "level": None, "disabled": True,
                        "cost": 0.0, "gain": 0.0, "roi_sec": float("inf"),
                        "time_to_afford": float("inf"), "eta_sec": float("inf"),
                        "parse_ok": False, "skip_reason": "no-title"
                    }
                    all_rows_metrics.append(m)
                    continue
        
                lvl = get_level_num(row)
                disabled = row_is_effectively_disabled(row)
        
                try:
                    price_box = row.find_element(By.XPATH, ".//div[contains(@class,'Upgrader_right-price_text')]")
                    price_raw = _norm(price_box.text or self.driver.execute_script(
                        "return arguments[0].textContent;", price_box) or "")
                except Exception:
                    price_raw = ""
        
                key = (title, lvl, price_raw)
                if key in seen:
                    m = {
                        "title": title, "level": lvl, "disabled": True,
                        "cost": 0.0, "gain": 0.0, "roi_sec": float("inf"),
                        "time_to_afford": float("inf"), "eta_sec": float("inf"),
                        "parse_ok": False, "skip_reason": "duplicate"
                    }
                    all_rows_metrics.append(m)
                    continue
                seen.add(key)
        
                # parse cost/gain → ROI
                parse_ok, reason = True, ""
                try:
                    cost, gain = self._extract_cost_and_gain(row)
                    cost = float(cost or 0.0)
                    gain = float(gain or 0.0)
                    if cost <= 0:
                        raise ValueError("cost<=0")
                    if gain <= 0:
                        raise ValueError("gain<=0")
                    roi_sec = self._roi_seconds(cost, gain)
                except Exception as e:
                    cost = locals().get("cost", 0.0)
                    gain = locals().get("gain", 0.0)
                    roi_sec = float("inf")
                    parse_ok, reason = False, f"parse-failed: {type(e).__name__}"
        
                # TTA & ETA
                if disabled:
                    deficit = max(cost - current_balance, 0.0)
                    if deficit <= 0:
                        tta = 0.0
                    else:
                        tta = (deficit / profit_per_sec) if profit_per_sec > 0 else float("inf")
                else:
                    tta = 0.0
                eta_sec = (tta + roi_sec) if (parse_ok and math.isfinite(roi_sec)) else float("inf")
        
                m = {
                    "title": title, "level": lvl, "disabled": disabled,
                    "cost": cost, "gain": gain,
                    "roi_sec": roi_sec, "time_to_afford": tta, "eta_sec": eta_sec,
                    "parse_ok": parse_ok, "skip_reason": reason
                }
        
                # ALWAYS record to the master list so every row is printed
                all_rows_metrics.append(m)
        
                # Partition for decision-making
                if parse_ok and not disabled and roi_sec <= MAX_ROI_SEC:
                    actionable_now.append(m)
                elif disabled and parse_ok:
                    disabled_considered.append(m)
                # long-ROI or parse-failed are handled only for printing, not actionable
        
            except Exception as e:
                all_rows_metrics.append({
                    "title": title or "Unknown", "level": None, "disabled": True,
                    "cost": 0.0, "gain": 0.0, "roi_sec": float("inf"),
                    "time_to_afford": float("inf"), "eta_sec": float("inf"),
                    "parse_ok": False, "skip_reason": f"loop-failed: {type(e).__name__}"
                })
                continue
        
        # --- 3) Group for pretty printing (priority 3) ---
        def _row_line(m, include_eta_when_disabled=True):
            title = m.get("title") or "Unknown"
            level = m.get("level")
            delta_str = self._human(m.get("gain", 0.0))
            cost_str  = self._human(m.get("cost", 0.0))
            roi_str   = f"ROI≈{self._hrs_str(m.get('roi_sec', float('inf')))}"
            tta_str   = f"TTA≈{self._hrs_str(m.get('time_to_afford', float('inf')))}"
            parts = [f"{title} (Lvl {level}) → Δ/sec={delta_str}, Cost={cost_str}, {roi_str}, {tta_str}"]
        
            if include_eta_when_disabled and m.get("disabled"):
                parts[0] += f", ETA≈{self._hrs_str(m.get('eta_sec', float('inf')))}"
            flags = []
            if m.get("disabled"):
                flags.append("disabled")
            if not m.get("parse_ok", True):
                flags.append(m.get("skip_reason") or "parse-failed")
            if math.isfinite(m.get("roi_sec", float('inf'))) and m["roi_sec"] > MAX_ROI_SEC:
                flags.append(f"roi>{MAX_ROI_DAYS}d")
            sr = m.get("skip_reason")
            if sr and sr not in flags:
                flags.append(sr)
            if flags:
                parts[0] += f" [{', '.join(flags)}]"
            return parts[0]
        
        # Split by sections
        ignored_long = [m for m in all_rows_metrics
                        if m.get("parse_ok", True)
                        and math.isfinite(m.get("roi_sec", float('inf')))
                        and m["roi_sec"] > MAX_ROI_SEC]
        
        available_now_print = [m for m in all_rows_metrics
                               if m.get("parse_ok", True)
                               and not m.get("disabled")
                               and math.isfinite(m.get("roi_sec", float('inf')))
                               and m["roi_sec"] <= MAX_ROI_SEC]
        
        not_yet_available = [m for m in all_rows_metrics
                             if m.get("parse_ok", True)
                             and m.get("disabled")]
        
        # Sort within each section for readability
        ignored_long.sort(key=lambda m: (m["roi_sec"], m["cost"], -m["gain"], m["title"] or ""))
        available_now_print.sort(key=lambda m: (m["roi_sec"], m["cost"], -m["gain"], m["title"] or ""))
        not_yet_available.sort(key=lambda m: (m["eta_sec"], m["cost"], -m["gain"], m["title"] or ""))
              
        self.output(f"Step {self.step} - Upgrades available with sensible ROI time: {len(available_now_print)}", 2)
        for m in available_now_print:
            self.output(_row_line(m, include_eta_when_disabled=False), 3)
        
        self.output(f"Step {self.step} - Upgrades not yet available (not yet affordable): {len(not_yet_available)}", 2)
        for m in not_yet_available:
            self.output(_row_line(m, include_eta_when_disabled=True), 3)

        # Print sections (priority 3)
        self.output(f"Step {self.step} - Available upgrades ignored due to excessive time to repay investment (> {MAX_ROI_DAYS}d): {len(ignored_long)}", 2)
        for m in ignored_long:
            self.output(_row_line(m, include_eta_when_disabled=False), 3)
        
        # --- 4) Decision: WAIT vs BUY ---
        actionable_now.sort(key=lambda m: (m["roi_sec"], m["cost"], -m["gain"], m["title"] or ""))
        disabled_considered.sort(key=lambda m: (m["eta_sec"], m["cost"], -m["gain"], m["title"] or ""))
        
        buy_now = True
        if USE_ETA_PLANNING:
            best_disabled = disabled_considered[0] if disabled_considered else None
            best_aff_now = actionable_now[0] if actionable_now else None
            if best_disabled and best_aff_now:
                if best_disabled["eta_sec"] + ETA_DECISION_MARGIN_SEC < best_aff_now["roi_sec"]:
                    buy_now = False
            elif best_disabled and not best_aff_now:
                buy_now = False
            else:
                buy_now = True
        
        # --- WAIT vs BUY strategy messaging (priority 2) ---
        
        if not buy_now:
            bd = disabled_considered[0]
            bd_title = bd['title']
            bd_eta   = self._hrs_str(bd['eta_sec'])
            bd_cost  = self._human(bd['cost'])
            bd_gain  = self._human(bd['gain'])
        
            if actionable_now:
                aff = actionable_now[0]
                aff_title = aff['title']
                aff_roi   = self._hrs_str(aff['roi_sec'])
                aff_cost  = self._human(aff['cost'])
                aff_gain  = self._human(aff['gain'])
                self.output(
                    f"Step {self.step} - Best strategy = WAIT: "
                    f"'{bd_title}' available in {bd_eta} "
                    f"beats already affordable '{aff_title}' which repays investment in {aff_roi}.",
                    2
                )
            else:
                self.output(
                    f"Step {self.step} - Best strategy = WAIT ⏳: "
                    f"Next available option will be '{bd_title}' (Δ/sec={bd_gain}, Cost={bd_cost}), affordable in {bd_eta}. ",
                    2
                )
            return 0
        
        # --- BUY path (priority 2), then proceed to click loop ---
        if actionable_now:
            aff = actionable_now[0]
            aff_title = aff['title']
            aff_roi   = self._hrs_str(aff['roi_sec'])
            aff_cost  = self._human(aff['cost'])
            aff_gain  = self._human(aff['gain'])
        
            if disabled_considered:
                bd = disabled_considered[0]
                bd_title = bd['title']
                bd_eta   = self._hrs_str(bd['eta_sec'])
                bd_cost  = self._human(bd['cost'])
                bd_gain  = self._human(bd['gain'])
                self.output(
                    f"Step {self.step} - Strategy: BUY ✅ "
                    f"Choosing '{aff_title}' now "
                    f"over waiting {bd_eta} for '{bd_title}'.",
                    2
                )
            else:
                self.output(
                    f"Step {self.step} - Strategy: BUY ✅ "
                    f"Best affordable '{aff_title}' (Δ/sec={aff_gain}, Cost={aff_cost}, ROI≈{aff_roi}).",
                    2
                )
        else:
            # Shouldn't happen if buy_now is True, but keep a guard
            self.output(
                f"Step {self.step} - Strategy: BUY ✅ but no affordable rows present (unexpected).",
                2
            )
    
        # --- 4) Decide: buy now (ROI-first) or wait (ETA-first)? ---
        if not actionable_now and not disabled_considered:
            self.output(f"Step {self.step} - No actionable or considered rows.", 2)
            return 0
    
        buy_now = True
        if USE_ETA_PLANNING:
            best_disabled = disabled_considered[0] if disabled_considered else None
            best_aff_now = actionable_now[0] if actionable_now else None
    
            if best_disabled and best_aff_now:
                if best_disabled["eta_sec"] + ETA_DECISION_MARGIN_SEC < best_aff_now["roi_sec"]:
                    buy_now = False
            elif best_disabled and not best_aff_now:
                buy_now = False
            else:
                buy_now = True
    
        if not buy_now:
            bd = disabled_considered[0]
            bd_title = bd['title']
            bd_eta   = self._hrs_str(bd['eta_sec'])
            bd_cost  = self._human(bd['cost'])
            bd_gain  = self._human(bd['gain'])
        
            if actionable_now:
                aff = actionable_now[0]
                aff_title = aff['title']
                aff_roi   = self._hrs_str(aff['roi_sec'])
                aff_cost  = self._human(aff['cost'])
                aff_gain  = self._human(aff['gain'])
                self.output(
                    f"Step {self.step} - Best strategy: WAIT "
                    f"Disabled '{bd_title}' (Δ/sec={bd_gain}, Cost={bd_cost}, ETA≈{bd_eta}) "
                    f"is better than affordable '{aff_title}' (Δ/sec={aff_gain}, Cost={aff_cost}, ROI≈{aff_roi}).",
                    2
                )
            else:
                self.output(
                    f"Step {self.step} - Best strategy: WAIT "
                    f"Best disabled '{bd_title}' (Δ/sec={bd_gain}, Cost={bd_cost}, ETA≈{bd_eta}) "
                    f"— no affordable upgrades available.",
                    2
                )
            return 0
            
        # --- BUY path (affordable ROI-first) ---
        if actionable_now:
            aff = actionable_now[0]
            aff_title = aff['title']
            aff_roi   = self._hrs_str(aff['roi_sec'])
            aff_cost  = self._human(aff['cost'])
            aff_gain  = self._human(aff['gain'])
        
            # If there is a disabled candidate, explain why we didn't wait
            if disabled_considered:
                bd = disabled_considered[0]
                bd_title = bd['title']
                bd_eta   = self._hrs_str(bd['eta_sec'])
                bd_cost  = self._human(bd['cost'])
                bd_gain  = self._human(bd['gain'])
                self.output(
                    f"Step {self.step} - Best strategy: BUY ✅ "
                    f"Choosing affordable '{aff_title}' (Δ/sec={aff_gain}, Cost={aff_cost}, ROI≈{aff_roi}) "
                    f"over disabled '{bd_title}' (Δ/sec={bd_gain}, Cost={bd_cost}, ETA≈{bd_eta}).",
                    2
                )
            else:
                self.output(
                    f"Step {self.step} - Strategy: BUY ✅ "
                    f"Best affordable '{aff_title}' (Δ/sec={aff_gain}, Cost={aff_cost}, ROI≈{aff_roi}).",
                    2
                )
        else:
            # Shouldn't happen because buy_now implies actionable_now, but keep a guard
            self.output(
                f"Step {self.step} - Strategy: BUY ✅ but no affordable rows present (unexpected).",
                2
            )
    
        # --- 5) Click affordable in best-first order ---
        ranked = []
        for m in actionable_now:
            lvl_key = m["level"] if isinstance(m["level"], int) else 10**9
            ranked.append((m["roi_sec"], m["cost"], lvl_key, m["title"]))
        ranked.sort(key=lambda x: (x[0], x[1], x[2], x[3]))
    
        targets = [
            ".//div[contains(@class,'Upgrader_right-wrap')]",
            ".//div[contains(@class,'Upgrader_right-price_text')]",
            ".//div[contains(@class,'Upgrader_right')]",
            ".//button",
            ".//*[self::div or self::span][contains(@class,'price') or contains(text(),'tflops')]",
        ]
    
        effective_clicks = 0
    
        for p in range(max_passes):
            acted = False
            for _, _, _, title in ranked:
                try:
                    row = find_row_by_title_exact(title)
                    if not row or row_is_effectively_disabled(row):
                        continue
    
                    ctrl = find_one(row, targets)
                    if not ctrl:
                        continue
    
                    lvl_before = get_level_num(row)
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
    def _parse_qty(self, text: str) -> float:
        """
        Accepts: "400.6M", "1.2B", "+260", "897.2M tflops", etc.
        Returns base units (float).
        """
        if text is None:
            return 0.0
        t = str(text).replace("\xa0", " ").strip()  # normalise NBSP -> space
    
        # Find the first number with an optional *single-letter* magnitude right after it.
        # Examples matched: "1.2B", "400.6M", "+260", "897.2M tflops"
        m = re.search(r'([+-]?\d+(?:\.\d+)?)([KMBTP])?\b', t, re.IGNORECASE)
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
        # self.output(f"Step {self.step} - raw cost text: '{price_txt}'", 3)
        cost = self._parse_qty(price_txt)
    
        # ----- GAIN (Income delta per sec) -----
        gain_el = row.find_element(By.XPATH, ".//div[contains(@class,'Upgrader_income')]/span[2]")
        gain_txt = (gain_el.text or "").strip()
        if not gain_txt:
            gain_txt = (self.driver.execute_script("return arguments[0].textContent;", gain_el) or "").strip()
        # self.output(f"Step {self.step} - raw gain text: '{gain_txt}'", 3)
        gain = self._parse_qty(gain_txt)
    
        return cost, gain
    
    def _roi_seconds(self, cost, gain):
        if not gain or gain <= 0:
            return float("inf")
        return cost / gain

    def _human(self, n):
        """Format a number with K/M/B/T/P suffix like the UI."""
        try:
            n = float(n)
        except Exception:
            return str(n)
        absn = abs(n)
        for suf, val in (("P", 1e15), ("T", 1e12), ("B", 1e9), ("M", 1e6), ("K", 1e3)):
            if absn >= val:
                return f"{n/val:.3g}{suf}"
        return f"{n:.3g}"
    
    def _hrs_str(self, seconds):
        """Nice hours formatting with ∞h for non-finite."""
        import math
        return "∞h" if not math.isfinite(seconds) else f"{seconds/3600.0:.2f}h"
        
def main():
    claimer = XNodeAUClaimer()
    claimer.run()

if __name__ == "__main__":

    main()









