"""Low-level scrolling, overlay handling and click fallbacks."""

from selenium.webdriver import ActionChains
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import StaleElementReferenceException, ElementClickInterceptedException, MoveTargetOutOfBoundsException


class ClickStrategiesMixin:
    """Low-level scrolling, overlay handling and click fallbacks. Uses the shared state on Claimer."""

    def clear_overlays(self, target_element, step):
        try:
            element_location = target_element.location_once_scrolled_into_view
            overlays = self.driver.find_elements(
                By.XPATH,
                "//*[contains(@style,'position: absolute') or contains(@style,'position: fixed')]"
            )
            overlays_cleared = 0
            for overlay in overlays:
                overlay_rect = overlay.rect
                if (overlay_rect['x'] <= element_location['x'] <= overlay_rect['x'] + overlay_rect['width'] and
                    overlay_rect['y'] <= element_location['y'] <= overlay_rect['y'] + overlay_rect['height']):
                    self.driver.execute_script("arguments[0].style.display = 'none';", overlay)
                    overlays_cleared += 1
            if overlays_cleared > 0:
                self.output(f"Step {step} - Removed {overlays_cleared} overlay(s) covering the target.", 3)
            return overlays_cleared
        except Exception as e:
            self.output(f"Step {step} - An error occurred while trying to clear overlays: {e}", 1)
            return 0

    def _center_in_scroll_parent(self, elem):
        # Scrolls either the nearest scrollable parent or the window to center the element
        self.driver.execute_script("""
          function getScrollableParent(el){
            while (el && el !== document.body){
              const s = getComputedStyle(el);
              const oy = s.overflowY;
              if ((oy === 'auto' || oy === 'scroll') && el.scrollHeight > el.clientHeight) return el;
              el = el.parentElement;
            }
            return null;
          }
          const el = arguments[0];
          const p = getScrollableParent(el);
          if (p){
            const r = el.getBoundingClientRect();
            const pr = p.getBoundingClientRect();
            p.scrollTop += (r.top - pr.top) - (pr.height/2 - r.height/2);
            p.scrollLeft += (r.left - pr.left) - (pr.width/2 - r.width/2);
          } else {
            el.scrollIntoView({block:'center', inline:'center'});
          }
        """, elem)

    def _js_click_variants(self, elem):
        # 1) Native element.click()
        try:
            self.driver.execute_script("arguments[0].click();", elem)
            return True
        except Exception:
            pass
    
        # 2) MouseEvent (bubbling + composed) – closer to real user click
        try:
            self.driver.execute_script("""
              const e = new MouseEvent('click', {
                bubbles: true, cancelable: true, composed: true, view: window
              });
              arguments[0].dispatchEvent(e);
            """, elem)
            return True
        except Exception:
            pass
    
        # 3) Pointer + mouse sequence on element (with composed)
        try:
            self.driver.execute_script("""
              const el = arguments[0];
              const hasPE = typeof window.PointerEvent === 'function';
              function fireMouse(type, tgt){
                tgt.dispatchEvent(new MouseEvent(type, {
                  bubbles: true, cancelable: true, composed: true, view: window
                }));
              }
              if (hasPE) el.dispatchEvent(new PointerEvent('pointerdown', {bubbles:true, cancelable:true, composed:true}));
              fireMouse('mousedown', el);
              if (hasPE) el.dispatchEvent(new PointerEvent('pointerup',   {bubbles:true, cancelable:true, composed:true}));
              fireMouse('mouseup', el);
              fireMouse('click', el);
            """, elem)
            return True
        except Exception:
            pass
    
        # 4) Click center point using elementFromPoint (some libs require coords)
        try:
            self.driver.execute_script("""
              const el = arguments[0];
              const r  = el.getBoundingClientRect();
              const x  = r.left + r.width/2;
              const y  = r.top  + r.height/2;
              const t  = document.elementFromPoint(x,y);
              if (t) {
                const e = new MouseEvent('click', {
                  bubbles:true, cancelable:true, composed:true, view:window, clientX:x, clientY:y
                });
                t.dispatchEvent(e);
              } else if (el && el.click) {
                el.click();
              }
            """, elem)
            return True
        except Exception:
            pass
    
        # 5) If inner child is targeted, try the nearest button ancestor directly
        try:
            self.driver.execute_script("""
              const el = arguments[0];
              const b = el.closest && el.closest('button');
              if (b) b.click();
            """, elem)
            return True
        except Exception:
            pass
    
        # 6) Focus + ENTER as a final nudge (some frameworks bind key handlers)
        try:
            self.driver.execute_script("""
              const el = arguments[0];
              const b = el.closest && el.closest('button');
              const tgt = b || el;
              if (tgt && typeof tgt.focus === 'function') {
                tgt.setAttribute('tabindex','0');
                tgt.focus({preventScroll:true});
                const e = new KeyboardEvent('keydown', {key:'Enter', code:'Enter', bubbles:true});
                tgt.dispatchEvent(e);
                const e2 = new KeyboardEvent('keyup', {key:'Enter', code:'Enter', bubbles:true});
                tgt.dispatchEvent(e2);
              }
            """, elem)
            return True
        except Exception:
            pass
    
        return False

    def _temporarily_disable_blockers(self, elem):
        # Disable pointer events on any element covering the target's center.
        return self.driver.execute_script("""
          const el = arguments[0];
          const r = el.getBoundingClientRect();
          const cx = r.left + r.width/2;
          const cy = r.top + r.height/2;
    
          // Gather elements stacked at the click point
          const hidden = [];
          const seen = new Set();
          for (let i=0; i<20; i++){
            const top = document.elementFromPoint(cx, cy);
            if (!top || seen.has(top)) break;
            seen.add(top);
    
            if (top !== el && !el.contains(top)) {
              const cs = getComputedStyle(top);
              // Only disable if it's visually blocking
              if (cs.pointerEvents !== 'none' && cs.visibility !== 'hidden' && cs.display !== 'none'){
                hidden.push([top, top.style.pointerEvents]);
                top.style.pointerEvents = 'none';
              }
            }
            // If we've exposed the target, stop early
            if (document.elementFromPoint(cx, cy) === el) break;
          }
          return hidden;
        """, elem)

    def _restore_blockers(self, state):
        # Restore pointer-events on previously disabled elements
        if not state:
            return
        try:
            self.driver.execute_script("""
              const items = arguments[0];
              for (const [node, oldPE] of items){
                if (node && node.style) node.style.pointerEvents = oldPE || '';
              }
            """, state)
        except Exception:
            pass

    def _safe_click_webelement(self, elem, action_description=""):
        try:
            # 1) Ensure in view (container aware)
            self._center_in_scroll_parent(elem)
    
            # 2) Wait for visible, enabled and with size
            WebDriverWait(self.driver, 5).until(EC.visibility_of(elem))
            WebDriverWait(self.driver, 5).until(lambda d: elem.is_enabled())
            WebDriverWait(self.driver, 5).until(
                lambda d: self.driver.execute_script(
                    "var r = arguments[0].getBoundingClientRect(); return (r.width>0 && r.height>0);", elem
                )
            )
    
            # 3) Try ActionChains click first
            try:
                ActionChains(self.driver).move_to_element(elem).pause(0.05).click(elem).perform()
                return elem
            except (MoveTargetOutOfBoundsException, ElementClickInterceptedException):
                # Will try JS paths below
                pass
    
            # 4) If something’s still blocking, temporarily disable blockers over center
            blockers = self._temporarily_disable_blockers(elem)
            try:
                if self._js_click_variants(elem):
                    self.output(f"Step {self.step} - JS click fallback used for {action_description}.", 3)
                    return elem
            finally:
                self._restore_blockers(blockers)
    
            # 5) As a final attempt, re-center & retry JS once more
            self._center_in_scroll_parent(elem)
            if self._js_click_variants(elem):
                self.output(f"Step {self.step} - JS click fallback (second attempt) used for {action_description}.", 3)
                return elem
    
            self.output(f"Step {self.step} - All click strategies failed for {action_description}.", 2)
            return None
    
        except StaleElementReferenceException:
            self.output(f"Step {self.step} - Element went stale during click for {action_description}.", 2)
            return None
        except Exception as e:
            self.output(f"Step {self.step} - Click failed: {type(e).__name__}: {e}", 2)
            return None
