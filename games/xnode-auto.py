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
        
    def upgrade_all(self, max_passes=2, per_row_wait=4):
        """Prefer upgrading by shortest ROI or (optionally) by shortest ETA = time_to_afford + ROI.
           Adds per-row debug: cost, gain, ROI, time_to_afford (if disabled), ETA.
        """
    
        # ---------- Tunables for "quant" planning ----------
        USE_ETA_PLANNING = True           # set False to keep pure ROI-first behaviour
        ETA_DECISION_MARGIN_SEC = 0       # require disabled best ETA to beat best affordable ROI by this much to "wait"
        # ---------------------------------------------------
    
        # --- tiny helpers local to this method ---
    
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
    
        def _norm(s: str) -> str:
            return (s or "").replace("\xa0", " ").strip()
      
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
    
        try:
            self.driver.execute_script("window.scrollTo(0, 0);")
        except Exception:
            pass
        for cont in containers:
            try:
                self.driver.execute_script("if (arguments[0].scrollTop !== undefined) arguments[0].scrollTop = 0;", cont)
            except Exception:
                pass
    
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
            f"Step {self.step} - containers(all/displayed): {len(all_containers)}/{sum(1 for c in all_containers if getattr(c,'is_displayed',lambda:True)())} | rows: {len(snapshot)}",
            3
        )
    
        if not snapshot:
            self.output(f"Step {self.step} - No Upgrader rows found in document (after fallbacks).", 2)
            return 0
    
        # --- 1a) Get current balance & profit/sec (for time_to_afford) ---
    
        def _parse_profit_per_sec():
            # Prefer cached if you stored it during "Step 114" parsing.
            try:
                if getattr(self, "profit_per_sec", None):
                    return float(self.profit_per_sec)
            except Exception:
                pass
            # Try to read from a known profit element (adjust selectors to your UI):
            try:
                el = self.driver.find_element(By.XPATH, "//*[contains(text(),'SEC') or contains(text(),'/SEC')]")
                raw = _norm(el.text or self.driver.execute_script("return arguments[0].textContent;", el) or "")
                # e.g. "+1.4M/SEC" -> "1.4M"
                m = re.search(r'([+-]?\d+(?:\.\d+)?\s*[KMBTP]?)\s*/\s*SEC', raw, re.I)
                if m:
                    return self._parse_qty(m.group(1))
            except Exception:
                pass
            return 0.0
    
        def _parse_current_balance():
            # Adjust to your balance element if available; fallback to 0.
            try:
                el = self.driver.find_element(By.XPATH, "//*[contains(@class,'balance') or contains(text(),'tflops')]")
                raw = _norm(el.text or self.driver.execute_script("return arguments[0].textContent;", el) or "")
                # Try to pick the first big number with magnitude
                m = re.search(r'([+-]?\d+(?:\.\d+)?\s*[KMBTP]?)\s*(?:tflops|TFLOPS)?', raw, re.I)
                if m:
                    return self._parse_qty(m.group(1))
            except Exception:
                pass
            return 0.0
    
        profit_per_sec = _parse_profit_per_sec()
        current_balance = _parse_current_balance()
    
        # --- 2) Scan rows → metrics, de-dupe, ROI, time_to_afford, ETA ---
    
        seen = set()
        all_rows_metrics = []
        actionable_now = []     # affordable & within ROI cap
        disabled_considered = []  # disabled but we compute time_to_afford & ETA
        import math
    
        for row in snapshot:
            try:
                try:
                    self.driver.execute_script(
                        "arguments[0].scrollIntoView({block:'center', inline:'nearest'});", row
                    )
                except Exception:
                    pass
    
                title = _norm(get_title(row))
                if not title:
                    all_rows_metrics.append({
                        "title": "", "level": None, "disabled": True,
                        "cost": 0.0, "gain": 0.0, "roi_sec": float("inf"),
                        "parse_ok": False, "skip_reason": "no-title"
                    })
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
                    all_rows_metrics.append({
                        "title": title, "level": lvl, "disabled": True,
                        "cost": 0.0, "gain": 0.0, "roi_sec": float("inf"),
                        "parse_ok": False, "skip_reason": "duplicate"
                    })
                    continue
                seen.add(key)
    
                # parse cost/gain
                try:
                    cost, gain = self._extract_cost_and_gain(row)
                    cost = float(cost or 0.0)
                    gain = float(gain or 0.0)
                    if cost <= 0:
                        raise ValueError("cost<=0")
                    if gain <= 0:
                        raise ValueError("gain<=0")
                    roi_sec = self._roi_seconds(cost, gain)
                    parse_ok = True
                    reason = ""
                except Exception as e:
                    cost = cost if 'cost' in locals() else 0.0
                    gain = gain if 'gain' in locals() else 0.0
                    roi_sec = float("inf")
                    parse_ok = False
                    reason = f"parse-failed: {type(e).__name__}"
    
                # time to afford & ETA
                if disabled:
                    # if disabled, we assume not enough balance for cost
                    deficit = max(cost - current_balance, 0.0)
                    tta = (deficit / profit_per_sec) if profit_per_sec > 0 else float("inf")
                else:
                    # already affordable: zero wait
                    tta = 0.0
                eta_sec = (tta + roi_sec) if (parse_ok and math.isfinite(roi_sec)) else float("inf")
    
                m = {
                    "title": title,
                    "level": lvl,
                    "disabled": disabled,
                    "cost": cost,
                    "gain": gain,
                    "roi_sec": roi_sec,
                    "time_to_afford": tta,
                    "eta_sec": eta_sec,
                    "parse_ok": parse_ok,
                    "skip_reason": reason
                }
    
                # filter per original ROI cap for "actionable now"
                if disabled:
                    m["skip_reason"] = m["skip_reason"] or "disabled"
                    disabled_considered.append(m)
                elif not parse_ok:
                    pass
                elif roi_sec > MAX_ROI_SEC:
                    m["skip_reason"] = f"roi>{MAX_ROI_DAYS}d"
                    all_rows_metrics.append(m)
                else:
                    actionable_now.append(m)
                    all_rows_metrics.append(m)
                    continue
    
                all_rows_metrics.append(m)
    
            except Exception as e:
                all_rows_metrics.append({
                    "title": _norm(locals().get("title", "")),
                    "level": locals().get("lvl", None),
                    "disabled": locals().get("disabled", None),
                    "cost": 0.0,
                    "gain": 0.0,
                    "roi_sec": float("inf"),
                    "time_to_afford": float("inf"),
                    "eta_sec": float("inf"),
                    "parse_ok": False,
                    "skip_reason": f"loop-failed: {type(e).__name__}"
                })
                continue
    
        # --- 3) Debug print & sort ---
    
        def _hrs(x):
            return (x / 3600.0) if math.isfinite(x) else float("inf")
    
        # Sort affordable by ROI-first (current behaviour)
        actionable_now.sort(key=lambda m: (m["roi_sec"], m["cost"], -m["gain"], m["title"] or ""))
    
        # Sort disabled by ETA-first (soonest benefit)
        disabled_considered.sort(key=lambda m: (m["eta_sec"], m["cost"], -m["gain"], m["title"] or ""))
    
        # Emit metrics (now includes TTA & ETA)
        for m in all_rows_metrics:
            roi = m.get("roi_sec", float("inf"))
            tta = m.get("time_to_afford", float("inf"))
            eta = m.get("eta_sec", float("inf"))
            flags = []
            if not m.get("parse_ok", True):
                flags.append(m.get("skip_reason") or "parse-failed")
            if m.get("disabled"):
                flags.append("disabled")
            if math.isfinite(roi) and roi > MAX_ROI_SEC:
                flags.append(f"roi>{MAX_ROI_DAYS}d")
            sr = m.get("skip_reason")
            if sr and sr not in flags:
                flags.append(sr)
            flag_txt = f" [{', '.join(flags)}]" if flags else ""
    
            self.output(
                f"Step {self.step} - ROI check: {m.get('title') or 'Unknown'} (Lvl {m.get('level')}) → "
                f"Δ/sec={m.get('gain',0.0):.3g}, Cost={m.get('cost',0.0):.3g}, "
                f"ROI≈{_hrs(roi):.2f}h, TTA≈{_hrs(tta):.2f}h, ETA≈{_hrs(eta):.2f}h{flag_txt}",
                3
            )
    
        # --- 4) Decide: buy now (ROI-first) or wait (ETA-first)? ---
    
        if not actionable_now and not disabled_considered:
            self.output(f"Step {self.step} - No actionable or considered rows.", 2)
            return 0
    
        buy_now = True
        chosen_title = None
    
        if USE_ETA_PLANNING:
            best_disabled = disabled_considered[0] if disabled_considered else None
            best_aff_now = actionable_now[0] if actionable_now else None
    
            if best_disabled and best_aff_now:
                # Compare disabled ETA vs affordable pure ROI
                if best_disabled["eta_sec"] + ETA_DECISION_MARGIN_SEC < best_aff_now["roi_sec"]:
                    buy_now = False
                    chosen_title = best_disabled["title"]
            elif best_disabled and not best_aff_now:
                buy_now = False
                chosen_title = best_disabled["title"]
            else:
                buy_now = True
                chosen_title = best_aff_now["title"] if best_aff_now else None
        else:
            buy_now = True
            chosen_title = actionable_now[0]["title"] if actionable_now else None
    
        if not buy_now:
            # We wait—log the reason clearly.
            bd = disabled_considered[0]
            self.output(
                f"Step {self.step} - Strategy: WAIT. Best disabled '{bd['title']}' ETA≈{_hrs(bd['eta_sec']):.2f}h "
                f"beats best affordable ROI≈{_hrs(actionable_now[0]['roi_sec']) if actionable_now else float('inf'):.2f}h.",
                2
            )
            return 0
    
        # If we’re here, we’ll proceed to buy in best-first order (affordable list)
        ranked = []
        for m in actionable_now:
            lvl_key = m["level"] if isinstance(m["level"], int) else 10**9
            ranked.append((m["roi_sec"], m["cost"], lvl_key, m["title"]))
        ranked.sort(key=lambda x: (x[0], x[1], x[2], x[3]))
    
        # target click areas (ordered fallbacks)
        targets = [
            ".//div[contains(@class,'Upgrader_right-wrap')]",
            ".//div[contains(@class,'Upgrader_right-price_text')]",
            ".//div[contains(@class,'Upgrader_right')]",
            ".//button",
            ".//*[self::div or self::span][contains(@class,'price') or contains(text(),'tflops')]",
        ]
    
        effective_clicks = 0
    
        def _get_level_by_title(ttl):
            r = find_row_by_title_exact(ttl)
            return get_level_num(r) if r else None
    
        for p in range(max_passes):
            acted = False
            for _, _, _, title in ranked:
                try:
                    row = find_row_by_title_exact(title)
                    if not row:
                        continue
                    if row_is_effectively_disabled(row):
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





