"""Element lookup, monitoring and click orchestration."""

import time
import random
from selenium.webdriver import ActionChains
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import NoSuchElementException, TimeoutException, StaleElementReferenceException


class InteractionsMixin:
    """Element lookup, monitoring and click orchestration. Uses the shared state on Claimer."""

    def move_and_click(self, xpath, wait_time, click, action_description, old_step, expectedCondition, attempts=5):
        """
        Wait for an element with a single overall timeout budget, retrying silently.
        On success, returns the WebElement (or None if not clicking). On failure, returns None.
        """
        def timer():
            return random.randint(1, 3) / 10.0
    
        self.output(f"Step {self.step} - Attempting to {action_description}...", 2)
    
        deadline = time.time() + float(wait_time)
        target_element = None
    
        # Helper: get element according to expected condition with fallback chain (no logs).
        def wait_for_element(remaining):
            wait = WebDriverWait(self.driver, max(0.5, remaining))
            if expectedCondition == "visible":
                return wait.until(EC.visibility_of_element_located((By.XPATH, xpath)))
            elif expectedCondition == "present":
                return wait.until(EC.presence_of_element_located((By.XPATH, xpath)))
            elif expectedCondition == "invisible":
                wait.until(EC.invisibility_of_element_located((By.XPATH, xpath)))
                if self.settings.get('debugIsOn'):
                    self.debug_information(f"{action_description} was found to be invisible", "check")
                return None
            elif expectedCondition == "clickable":
                try:
                    return wait.until(EC.element_to_be_clickable((By.XPATH, xpath)))
                except TimeoutException:
                    try:
                        return wait.until(EC.visibility_of_element_located((By.XPATH, xpath)))
                    except TimeoutException:
                        return wait.until(EC.presence_of_element_located((By.XPATH, xpath)))
            else:
                return wait.until(EC.presence_of_element_located((By.XPATH, xpath)))
    
        for attempt in range(1, attempts + 1):
            remaining = deadline - time.time()
            if remaining <= 0:
                break
    
            try:
                target_element = wait_for_element(remaining)
                if target_element is None:
                    # 'invisible' path succeeded (nothing to click/do)
                    return None
    
                # Ensure in-view; only log once if we had to scroll
                in_view = self.driver.execute_script("""
                    var elem = arguments[0], box = elem.getBoundingClientRect();
                    if (!(box.top >= 0 && box.left >= 0 &&
                          box.bottom <= (window.innerHeight || document.documentElement.clientHeight) &&
                          box.right  <= (window.innerWidth  || document.documentElement.clientWidth))) {
                        elem.scrollIntoView({block: 'center', inline: 'center'});
                        return false;
                    }
                    return true;
                """, target_element)
                if not in_view:
                    # keep this low-noise
                    if self.settings.get('debugIsOn'):
                        self.debug_information(f"{action_description} was out of bounds and scrolled into view", "info")
    
                # Staleness guard
                try:
                    _ = target_element.tag_name
                except StaleElementReferenceException:
                    try:
                        target_element = self.driver.find_element(By.XPATH, xpath)
                    except Exception:
                        # Try again within the same budget
                        time.sleep(0.1 + timer())
                        continue
    
                if click:
                    self.clear_overlays(target_element, self.step)
                    result = self._safe_click_webelement(target_element, action_description=action_description)
                    if result is not None:
                        if self.settings.get('debugIsOn'):
                            self.debug_information(f"Moved & clicked {action_description}", "success")
                        return target_element
                    # click failed; brief backoff and retry within same budget
                    time.sleep(0.2 + timer())
                    continue
                else:
                    if self.settings.get('debugIsOn'):
                        self.debug_information(f"Moved to {action_description} without clicking", "no click")
                    return target_element
    
            except TimeoutException:
                # silent retry within the same overall budget
                continue
            except StaleElementReferenceException:
                # silent retry
                continue
            except Exception as e:
                if "has no size and location" in str(e):
                    self.output(f"Step {self.step} - Element issue during {action_description}: Element not properly located or sized.", 1)
                    if self.settings.get('debugIsOn'):
                        self.debug_information(f"Fatal error during {action_description}: {str(e)}", "error")
                    return None
                # Non-fatal: retry within budget
                time.sleep(0.1 + timer())
                continue
    
        # Final failure (single line)
        self.output(f"Step {self.step} - {action_description} not found/clickable after {attempts} attempts (~{wait_time}s).", 2)
        if self.settings.get('debugIsOn'):
            self.debug_information(f"{action_description} not found after {attempts} attempts", "error")
        return None

    def click_element(self, xpath, timeout=30, action_description=""):
        try:
            element = WebDriverWait(self.driver, timeout).until(
                EC.element_to_be_clickable((By.XPATH, xpath))
            )
            if self.settings['debugIsOn']:
                self.debug_information(f"ClickElem {action_description} - Element located", "info")
            res = self._safe_click_webelement(element, action_description=action_description)
            return res is not None
        except TimeoutException:
            self.output(f"Step {self.step} - Element not found within timeout: {xpath}. Skipping click.", 2)
            if self.settings['debugIsOn']:
                self.debug_information(f"ClickElem {action_description} timed out waiting for element", "error")
            return False
        except Exception as e:
            self.output(f"Step {self.step} - An error occurred during {action_description}: {type(e).__name__}: {e}", 3)
            if self.settings['debugIsOn']:
                self.debug_information(f"ClickElem {action_description} fatal error: {str(e)}", "error")
            return False
    
        except (StaleElementReferenceException, Exception) as e:
            if "has no size and location" in str(e):
                self.output(f"Step {self.step} - Element issue during {action_description}: Element not properly located or sized.", 1)
                if self.settings['debugIsOn']:
                    self.debug_information(f"ClickElem {action_description} fatal error: {str(e)}", "error")
                return False
            self.output(f"Step {self.step} - An error occurred during {action_description}.", 3)
            if self.settings['debugIsOn']:
                self.debug_information(f"ClickElem {action_description} fatal error: {str(e)}", "error")
            return False

    def brute_click(self, xpath, timeout=30, action_description="", state_check=None, post_click_wait=0.6):
        """
        Brute-force click:
          1) Ensure element is present & in view (no click yet).
          2) Try ActionChains click -> JS click variants -> temporarily disable blockers and retry ->
             click closest('button') -> final center/coords click.
          3) After each attempt, consider success if:
               A) element disappears, or
               B) state_check() returns True, or
               C) element's DOM 'signature' changes (outerHTML/id).
        Returns True on likely success, False otherwise.
        """
    
        # ---- 0) Ensure present & in view (no click yet)
        if not self.move_and_click(
            xpath, 10, False,
            f"locate the element to Brute Click ({action_description})",
            self.step, "clickable"
        ):
            self.output(f"Step {self.step} - Element not found or not scrollable: {xpath}", 2)
            if self.settings.get('debugIsOn'):
                self.debug_information(f"BruteClick locate failed: {action_description}", "error")
            return False
    
        end = time.time() + timeout
    
        def html_sig(el):
            """Lightweight signature of the element for change detection."""
            try:
                outer = self.driver.execute_script("return arguments[0].outerHTML.slice(0, 200);", el) or ""
                return (el.get_attribute("id") or "", outer)
            except Exception:
                return None
    
        def js_click_variants(el) -> bool:
            """Progressively more realistic JS click paths."""
            # a) Native element.click()
            try:
                self.driver.execute_script("arguments[0].click();", el)
                return True
            except Exception:
                pass
    
            # b) MouseEvent bubbling
            try:
                self.driver.execute_script("""
                    const e = new MouseEvent('click', {bubbles:true, cancelable:true, composed:true, view:window});
                    arguments[0].dispatchEvent(e);
                """, el)
                return True
            except Exception:
                pass
    
            # c) Pointer + mouse sequence on the element (PointerEvent may not exist)
            try:
                self.driver.execute_script("""
                    const el = arguments[0];
                    const hasPE = typeof window.PointerEvent === 'function';
                    function fireMouse(type, tgt){ tgt.dispatchEvent(new MouseEvent(type, {bubbles:true, cancelable:true, view:window})); }
                    if (hasPE) el.dispatchEvent(new PointerEvent('pointerdown', {bubbles:true, cancelable:true}));
                    fireMouse('mousedown', el);
                    if (hasPE) el.dispatchEvent(new PointerEvent('pointerup',   {bubbles:true, cancelable:true}));
                    fireMouse('mouseup', el);
                    fireMouse('click', el);
                """, el)
                return True
            except Exception:
                pass
    
            # d) Center click using elementFromPoint (some libs require coords)
            try:
                self.driver.execute_script("""
                  const el = arguments[0];
                  const r  = el.getBoundingClientRect();
                  const x  = r.left + r.width/2;
                  const y  = r.top  + r.height/2;
                  const t  = document.elementFromPoint(x,y);
                  if (t) {
                    const e = new MouseEvent('click', {bubbles:true, cancelable:true, composed:true, view:window, clientX:x, clientY:y});
                    t.dispatchEvent(e);
                  } else if (el && el.click) {
                    el.click();
                  }
                """, el)
                return True
            except Exception:
                pass
    
            return False
    
        while time.time() < end:
            # ---- 1) (Re)locate current element
            try:
                el = self.driver.find_element(By.XPATH, xpath)
            except Exception:
                # If not found at loop start, a prior iteration probably succeeded
                self.output(f"Step {self.step} - Click successful: element not found before attempt.", 2)
                return True
    
            # ---- 2) Pre-click: scroll, clear overlays, record signature
            try:
                self.driver.execute_script("arguments[0].scrollIntoView({block:'center', inline:'center'});", el)
            except Exception:
                pass
            try:
                self.clear_overlays(el, self.step)
            except Exception:
                pass
    
            pre_sig = html_sig(el)
    
            # ---- 3) Attempt chain
            clicked = False
    
            # 3.1 Native (ActionChains)
            try:
                ActionChains(self.driver).move_to_element(el).pause(0.05).click(el).perform()
                clicked = True
            except Exception:
                # 3.2 JS variants
                clicked = js_click_variants(el)
    
                # 3.3 Temporarily disable blockers and retry JS
                if not clicked:
                    blockers = None
                    try:
                        blockers = self._temporarily_disable_blockers(el)
                        clicked = js_click_variants(el)
    
                        # 3.4 Click closest button ancestor
                        if not clicked:
                            try:
                                self.driver.execute_script("const b = arguments[0].closest('button'); if (b) b.click();", el)
                                clicked = True
                            except Exception:
                                pass
    
                        # 3.5 Final center-pointer sequence on top element at coords
                        if not clicked:
                            try:
                                self.driver.execute_script("""
                                    const el = arguments[0];
                                    const r  = el.getBoundingClientRect();
                                    const x  = r.left + r.width/2;
                                    const y  = r.top  + r.height/2;
                                    const t  = document.elementFromPoint(x,y) || el;
                                    function fire(type, tgt){
                                      tgt.dispatchEvent(new MouseEvent(type, {bubbles:true, cancelable:true, view:window, clientX:x, clientY:y}));
                                    }
                                    if (typeof window.PointerEvent === 'function') {
                                      t.dispatchEvent(new PointerEvent('pointerdown', {bubbles:true, cancelable:true, clientX:x, clientY:y}));
                                    }
                                    fire('mousedown', t);
                                    if (typeof window.PointerEvent === 'function') {
                                      t.dispatchEvent(new PointerEvent('pointerup',   {bubbles:true, cancelable:true, clientX:x, clientY:y}));
                                    }
                                    fire('mouseup', t); fire('click', t);
                                """, el)
                                clicked = True
                            except Exception:
                                pass
                    finally:
                        try:
                            self._restore_blockers(blockers)
                        except Exception:
                            pass
    
            # ---- 4) Give UI a moment to react
            time.sleep(post_click_wait)
    
            # ---- 5) Success checks
            # A) Disappeared?
            try:
                self.driver.find_element(By.XPATH, xpath)
                still_there = True
            except NoSuchElementException:
                still_there = False
    
            if not still_there:
                self.output(f"Step {self.step} - BruteClick success: element disappeared.", 3)
                return True
    
            # B) Custom state check?
            if callable(state_check):
                try:
                    if state_check():
                        self.output(f"Step {self.step} - BruteClick success: state_check passed.", 3)
                        return True
                except Exception:
                    pass
    
            # C) Signature changed?
            try:
                el2 = self.driver.find_element(By.XPATH, xpath)
                post_sig = html_sig(el2)
            except Exception:
                self.output(f"Step {self.step} - BruteClick success: element replaced and then missing.", 3)
                return True
    
            if pre_sig is not None and post_sig is not None and post_sig != pre_sig:
                self.output(f"Step {self.step} - BruteClick probable success: DOM signature changed.", 3)
                return True
    
            # Otherwise, small backoff and try again
            time.sleep(0.1)
    
        self.output(f"Step {self.step} - Brute click timed out without clear success. ({action_description})", 2)
        if self.settings.get('debugIsOn'):
            self.debug_information(f"BruteClick timeout: {action_description}", "error")
        return False

    def element_still_exists_by_id(self, element_id):
        """Check if an element still exists by its ID."""
        try:
            element = self.driver.find_element(By.ID, element_id)
            return element.is_displayed()
        except NoSuchElementException:
            return False

    def monitor_element(self, xpath, timeout=8, action_description="no description"):
        end_time = time.time() + timeout
        first_time = True
        if self.settings['debugIsOn']:
            self.debug_information(f"MonElem {action_description}","check")
        while time.time() < end_time:
            try:
                elements = self.driver.find_elements(By.XPATH, xpath)
                if first_time:
                    self.output(f"Step {self.step} - Found {len(elements)} elements with XPath: {xpath} for {action_description}", 3)
                    first_time = False

                texts = [element.text.replace('\n', ' ').replace('\r', ' ').strip() for element in elements if element.text.strip()]
                if texts:
                    return ' '.join(texts)
            except (StaleElementReferenceException, TimeoutException, NoSuchElementException):
                pass
            except Exception as e:
                self.output(f"An error occurred: {e}", 3)
                if self.settings['debugIsOn']:
                    self.debug_information(f"MonElem failed on {action_description}","error")
                return False
        return False
