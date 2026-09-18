"""Telegram mini-app launching, links and iframe navigation."""

import os
import shutil
import time
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys
from selenium.common.exceptions import TimeoutException


class WebAppMixin:
    """Telegram mini-app launching, links and iframe navigation. Uses the shared state on Claimer."""

    def launch_iframe(self):
        def wait_ready(driver, timeout=30):
            WebDriverWait(driver, timeout).until(
                lambda d: d.execute_script("return document.readyState") == "complete"
            )
    
        self.driver = self.get_driver()
        self.driver.set_window_size(1920, 1080)
    
        # start with clean screenshots dir (once per session)
        if int(self.step) < 101:
            if os.path.exists(self.screenshots_path):
                shutil.rmtree(self.screenshots_path)
            os.makedirs(self.screenshots_path)
    
        # --- Initial bounce and QR sanity check (non-fatal) ---
        try:
            self.driver.get("https://www.google.com/")
            wait_ready(self.driver)
            self.driver.get(self.url)  # your deep link like https://web.telegram.org/k/#@IcebergAppBot
            wait_ready(self.driver)
            time.sleep(5)  # let TG lazy pieces attach
    
            self.output(f"Step {self.step} - Attempting QR presence check (expecting none).", 2)
            if self.settings.get('debugIsOn'):
                self.debug_information("QR code check during session start", "check")
    
            try:
                WebDriverWait(self.driver, 5).until(
                    EC.visibility_of_element_located((By.XPATH, "//canvas[@class='qr-canvas']"))
                )
                self.output(
                    f"Step {self.step} - QR visible (likely logged out). You may see follow-up input errors.",
                    2
                )
            except TimeoutException:
                self.output(f"Step {self.step} - No QR detected; proceeding.", 3)
    
        except Exception as e:
            self.output(f"Step {self.step} - Initial load error: {e}", 1)
    
        self.increase_step()
    
        # --- Verify chat title (up to 3 tries), rebouncing via Google between tries ---
        title_xpath = "(//div[@class='user-title']//span[contains(@class,'peer-title')])[1]"
        verified = False
        for attempt in range(1, 4):
            try:
                WebDriverWait(self.driver, 30).until(
                    EC.visibility_of_element_located((By.XPATH, title_xpath))
                )
                title = (self.monitor_element(title_xpath, 8, "Get current page title") or "").strip()
                if title:
                    self.output(f"Step {self.step} - The current page title is: {title}", 3)
                    verified = True
                    break
                else:
                    self.output(f"Step {self.step} - Attempt {attempt}: title element present but empty.", 3)
            except TimeoutException:
                self.output(f"Step {self.step} - Attempt {attempt}: title not visible yet.", 3)
                if self.settings.get('debugIsOn'):
                    self.debug_information("App title check during telegram load", "check")
    
            # Re-bounce to force TG to respect the deep link next try
            try:
                self.driver.get("https://www.google.com/")
                wait_ready(self.driver)
                self.driver.get(self.url)
                wait_ready(self.driver)
                time.sleep(3)
            except Exception as e:
                self.output(f"Step {self.step} - Re-bounce error before attempt {attempt+1}: {e}", 2)
    
        if not verified:
            self.output(
                "STATUS: Could not reach the game after 3 attempts. "
                "You may need to manually bump the game up in your Telegram chat list.",
                1
            )
    
        # --- Continue with the existing flow ---
        self.increase_step()
    
        # Press START if present (some chats need this to reveal the thread)
        self.move_and_click("//button[contains(., 'START')]", 8, True,
                            "check for the start button (may not be present)", self.step, "clickable")
        self.increase_step()
    
        # Find or send a working deep-link
        if self.find_working_link(self.step):
            self.increase_step()
        else:
            self.send_start(self.step)
            self.increase_step()
            self.find_working_link(self.step)
            self.increase_step()
    
        # Click 'Launch' in the popup, if present
        self.move_and_click(
            "//button[contains(@class,'popup-button') and contains(.,'Launch')]",
            8, True, "click the 'Launch' button (probably not present)", self.step, "clickable"
        )
        self.increase_step()
    
        # Patch platform and switch into game iframe
        self.replace_platform()
        self.select_iframe(self.step)
        self.increase_step()
    
        self.output(f"Step {self.step} - Preparatory steps complete, handing over to main flow…", 2)
        time.sleep(2)

    def replace_platform(self):
        # Insert the platform replacement code here
        self.output(f"Step {self.step} - Attempting to replace platform in iframe URL if necessary...", 2)
        try:
            wait = WebDriverWait(self.driver, 20)
            # Locate the container div with the specified class name
            container = wait.until(EC.presence_of_element_located((By.CLASS_NAME, 'web-app-body')))
            # Find the iframe within the located container
            iframe = container.find_element(By.TAG_NAME, "iframe")
            # Get the iframe src
            iframe_url = iframe.get_attribute("src")

            if "tgWebAppPlatform=web" in iframe_url:
                # Replace 'tgWebAppPlatform=web' with the desired platform
                iframe_url = iframe_url.replace("tgWebAppPlatform=web", f"tgWebAppPlatform={self.default_platform}")
                self.output(f"Step {self.step} - Platform 'web' found in iframe URL and replaced with '{self.default_platform}'.", 2)
                # Update the iframe src to reload it
                self.driver.execute_script("arguments[0].src = arguments[1];", iframe, iframe_url)
            else:
                self.output("Step {self.step} - No 'tgWebAppPlatform=web' parameter found in the iframe URL.", 2)
        except TimeoutException:
            self.output(f"Step {self.step} - Failed to locate the iframe within 'web-app-body' container.", 3)
        except Exception as e:
            self.output(f"Step {self.step} - An error occurred while attempting to modify the iframe URL: {e}", 3)
        self.increase_step()

        # Give it a few seconds to reload
        time.sleep(5)

    def select_iframe(self, old_step, iframe_id=None, iframe_container_class="web-app-body"):
        self.output(f"Step {self.step} - Attempting to switch to the app's iFrame with id '{iframe_id}' or within '{iframe_container_class}'...", 2)

        try:
            wait = WebDriverWait(self.driver, 20)
            
            if iframe_id:
                # Try locating the iframe directly by ID
                iframe = wait.until(EC.presence_of_element_located((By.ID, iframe_id)))
                self.driver.switch_to.frame(iframe)
                self.output(f"Step {self.step} - Successfully switched to iframe with id '{iframe_id}'.", 3)
                if self.settings['debugIsOn']:
                    self.debug_information("successfully switched to iFrame by id", "success")
            else:
                # Locate the container div with the specified class name
                container = wait.until(EC.presence_of_element_located((By.CLASS_NAME, iframe_container_class)))
                # Find the iframe within the located container
                iframe = container.find_element(By.TAG_NAME, "iframe")
                # Switch to the iframe
                self.driver.switch_to.frame(iframe)
                self.output(f"Step {self.step} - Successfully switched to the app's iFrame within '{iframe_container_class}'.", 3)
                if self.settings['debugIsOn']:
                    self.debug_information("successfully switched to iFrame within container", "success")

        except TimeoutException:
            self.output(f"Step {self.step} - Failed to find or switch to the iframe with id '{iframe_id}' or within '{iframe_container_class}' within the timeout period.", 3)
            if self.settings['debugIsOn']:
                self.debug_information("timeout while trying to switch to iFrame", "error")
        except Exception:
            self.output(f"Step {self.step} - An error occurred while attempting to switch to the iframe with id '{iframe_id}' or within '{iframe_container_class}'.", 3)
            if self.settings['debugIsOn']:
                self.debug_information("an unspecified error occurred during switch to iFrame", "error")

    def send_start(self, old_step):
        xpath = "//div[contains(@class, 'input-message-container')]/div[contains(@class, 'input-message-input')][1]"
        
        def attempt_send_start():
            chat_input = self.move_and_click(xpath, 5, False, "find the chat window message input box", self.step, "present")
            if chat_input:
                self.increase_step()
                self.output(f"Step {self.step} - Attempting to send the '/start' command...",2)
                chat_input.send_keys("/start")
                chat_input.send_keys(Keys.RETURN)
                self.output(f"Step {self.step} - Successfully sent the '/start' command.\n",3)
                if self.settings['debugIsOn']:
                    self.debug_information("we sent the start command to the chat window","success")
                return True
            else:
                self.output(f"Step {self.step} - Failed to find the message input box.\n",1)
                return False

        if not attempt_send_start():
            # Attempt failed, try restoring from backup and retry
            self.output(f"Step {self.step} - Attempting to restore from backup and retry.\n",2)
            if self.restore_from_backup(self.backup_path):
                if not attempt_send_start():  # Retry after restoring backup
                    self.output(f"Step {self.step} - Retried after restoring backup, but still failed to send the '/start' command.\n",1)
            else:
                self.output(f"Step {self.step} - Backup restoration failed or backup directory does not exist.\n",1)

    def find_working_link(self, old_step, custom_xpath=None):
        # Use custom_xpath if provided, otherwise fall back to self.start_app_xpath
        start_app_xpath = custom_xpath if custom_xpath is not None else self.start_app_xpath
        self.output(f"Step {self.step} - Attempting to open a link for the app: {start_app_xpath}...", 2)
    
        try:
            # Wait for elements to be present in the DOM
            start_app_buttons = WebDriverWait(self.driver, 10).until(
                EC.presence_of_all_elements_located((By.XPATH, start_app_xpath))
            )
    
            num_buttons = len(start_app_buttons)
            self.output(f"Step {self.step} - Found {num_buttons} matching link(s) by presence.", 2)
    
            if num_buttons == 0:
                self.output(f"Step {self.step} - No buttons found with XPath: {start_app_xpath}\n", 1)
                if self.settings['debugIsOn']:
                    self.debug_information("find working link - no buttons found", "error")
                return False
    
            # Iterate through buttons in reverse order
            for idx in range(num_buttons - 1, -1, -1):  # Reverse order
                link_xpath = f"({start_app_xpath})[{idx + 1}]"  # XPath indexes start from 1
                self.output(f"Step {self.step} - Attempting to click link {idx + 1}...", 2)
    
                # Use move_and_click to handle visibility, scrolling, and clicking
                if self.move_and_click(link_xpath, 10, True, "find game launch link", self.step, "clickable"):
                    self.output(f"Step {self.step} - Successfully opened a link for the app.\n", 3)
                    if self.settings['debugIsOn']:
                        self.debug_information("successfully opened a game start link", "success")
                    return True
                else:
                    self.output(f"Step {self.step} - Link {idx + 1} was not clickable, moving on to next link...", 2)
    
            # If none of the links worked
            self.output(f"Step {self.step} - None of the matching links were clickable.\n", 1)
            if self.settings['debugIsOn']:
                self.debug_information("no working game link", "error")
            return False
    
        except TimeoutException:
            self.output(f"Step {self.step} - Failed to find the 'Open Wallet' button within the expected timeframe.\n", 1)
            if self.settings['debugIsOn']:
                self.debug_information("timeout while trying to open the game", "error")
            return False
        except Exception as e:
            self.output(f"Step {self.step} - An error occurred while trying to open the app: {e}\n", 1)
            if self.settings['debugIsOn']:
                self.debug_information("unspecified error while trying to launch the game", "error")
            return False
