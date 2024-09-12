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

from claimer import Claimer

class HamsterKombatClaimer(Claimer):

    def initialize_settings(self):
        super().initialize_settings()
        self.script = "games/hamsterkombat.py"
        self.prefix = "HammyKombat:"
        self.url = "https://web.telegram.org/k/#@hamster_kombat_bot"
        self.pot_full = "Filled"
        self.pot_filling = "Mining"
        self.seed_phrase = None
        self.forceLocalProxy = True
        self.forceRequestUserAgent = False
        self.start_app_xpath = "//button//span[contains(text(), 'Play in 1')] | //div[contains(@class, 'new-message-bot-commands-view') and contains(text(), 'Play')]"

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
            
    def launch_iframe(self):
        super().launch_iframe()

        # Open tab in main window
        self.driver.switch_to.default_content()

        iframe = self.driver.find_element(By.TAG_NAME, "iframe")
        iframe_url = iframe.get_attribute("src")
        
        # Check if 'tgWebAppPlatform=' exists in the iframe URL before replacing
        if "tgWebAppPlatform=" in iframe_url:
            # Replace both 'web' and 'weba' with the dynamic platform
            iframe_url = iframe_url.replace("tgWebAppPlatform=web", f"tgWebAppPlatform={self.default_platform}")
            iframe_url = iframe_url.replace("tgWebAppPlatform=weba", f"tgWebAppPlatform={self.default_platform}")
            self.output(f"Platform found and replaced with '{self.default_platform}'.", 2)
        else:
            self.output("No tgWebAppPlatform parameter found in the iframe URL.", 2)

        self.driver.execute_script(f"location.href = '{iframe_url}'")

    def full_claim(self):
        self.step = "100"
        self.launch_iframe()
        
        # Try to claim the daily reward if it's there
        xpath = "//button[span[text()='Claim']]"
        success = self.move_and_click(xpath, 20, True, "look for the Daily Reward claim button.", self.step, "clickable")
        self.increase_step()
    
        # And the "thank you hamster"
        xpath = "//button[span[text()='Thank you, Hamster']]"
        success = self.move_and_click(xpath, 20, True, "look for the 'Thank you hamster' bonus.", self.step, "clickable")
        self.increase_step()
        
        # Capture initial values before the claim
        initial_remains = self.get_remains()  # Capture the initial remains
        initial_balance = self.get_balance(False)  # Capture the initial balance (before the claim)
        
        # Ensure initial balance is captured correctly
        if initial_balance is None:
            self.output(f"Step {self.step} - Failed to retrieve the initial balance.", 2)

        self.output(f"Step {self.step} - Initial Remains: {initial_remains}, Initial Balance: {initial_balance}", 3)
    
        # Fetch remains after claiming but before clicking
        starting_clicks = initial_remains
        self.output(f"Step {self.step} - Starting clicks (Remains after claim): {starting_clicks}", 3)
    
        # Only call click_ahoy if starting_clicks is a number and greater than 0
        if isinstance(starting_clicks, (int, float)) and starting_clicks > 0:
            self.click_ahoy(starting_clicks)
    
            # Fetch remains again after click_ahoy
        remains_after_clicks = self.get_remains()
    
        # Display remaining clicks if it's a valid number
        if isinstance(remains_after_clicks, (int, float)):
            self.output(f"Step {self.step} - Remaining clicks: {remains_after_clicks}", 3)
        else:
            self.output(f"Step {self.step} - Unable to retrieve valid remains after clicks.", 3)
    
        # Return the current profit per hour
        self.get_profit_hour(True)

        # Fetch the final balance after clicks
        final_balance = self.get_balance(True)
    
        # Ensure final balance is captured correctly
        if final_balance is None:
            self.output(f"Step {self.step} - Failed to retrieve the final balance.", 2)

        # Calculate differences
        remains_diff = initial_remains - remains_after_clicks if isinstance(initial_remains, (int, float)) and isinstance(remains_after_clicks, (int, float)) else 0
        balance_diff = final_balance - initial_balance if isinstance(initial_balance, (int, float)) and isinstance(final_balance, (int, float)) else 0
    
        # Output the result with priority 1
        self.output(f"STATUS: We used {remains_diff} energy to gain {balance_diff} more tokens.", 1)

        random_timer = random.randint(20, 60)
        self.output(f"Step {self.step} - Recharging energy for {random_timer} minutes.", 3)
        return random_timer

    def get_balance(self, claimed=False):

        prefix = "After" if claimed else "Before"
        default_priority = 2 if claimed else 3

        # Dynamically adjust the log priority
        priority = max(self.settings['verboseLevel'], default_priority)

        # Construct the specific balance XPath
        balance_text = f'{prefix} BALANCE:'
        balance_xpath = f"//div[@class='user-balance-large-inner']/p"

        try:
            element = self.monitor_element(balance_xpath, 10, "get balance")

            # Check if element is not None and process the balance
            if element:
                cleaned_balance = self.strip_html_and_non_numeric(element)
                self.output(f"Step {self.step} - {balance_text} {cleaned_balance}", priority)
                return float(cleaned_balance)
        except NoSuchElementException:
            self.output(f"Step {self.step} - Element containing '{prefix} Balance:' was not found.", priority)
        except Exception as e:
            self.output(f"Step {self.step} - An error occurred: {str(e)}", priority)  # Provide error as string for logging

        # Increment step function, assumed to handle next step logic
        self.increase_step()


    def get_remains(self):
        remains_xpath = "//div[@class='user-tap-energy']/p"
        try:
            # Move to and click the element if necessary
            first = self.move_and_click(remains_xpath, 10, False, "remove overlays", self.step, "visible")
            
            # Monitor the element to get its content
            remains_element = self.monitor_element(remains_xpath, 15, "get reamining clicks")
            
            # Check if the remains_element is found and get its text content
            if remains_element:
                remains_text = remains_element.strip()  # Get the text and strip whitespace
                if " / " in remains_text:
                    n1, n2 = remains_text.split(" / ")  # Split the string into two parts
                    n1, n2 = int(n1), int(n2)  # Convert both parts to integers
                    
                    # Output the result with priority 3
                    self.output(f"Step {self.step} - {n1} energry remaining of a maximum {n2}.", 3)
                    
                    # Return n1 (the remaining clicks)
                    return n1
                else:
                    # If the text doesn't match the expected format
                    self.output(f"Step {self.step} - Unexpected format: '{remains_text}'", 3)
                    return None
            else:
                # If the element wasn't found
                self.output(f"Step {self.step} - Element containing 'Remains' was not found.", 3)
                return None
        except NoSuchElementException:
            # Handle the case where the element is not found
            self.output(f"Step {self.step} - Element containing 'Remains' was not found.", 3)
            return None
        except Exception as e:
            # Handle any other exceptions that might occur
            self.output(f"Step {self.step} - An error occurred: {str(e)}", 3)
            return None

    def click_ahoy(self, remains):
        xpath = "//div[@class='user-tap-energy']/p"
        self.move_and_click(xpath, 10, False, "get closer to the hamster!", self.step, "visible")
    
        self.output(f"Step {self.step} - We have {remains} targets to click. This might take some time!", 3)
    
        try:
            # Find the reference element using XPath to ensure page has loaded
            element = self.driver.find_element(By.XPATH, xpath)
        except Exception as e:
            self.output(f"Step {self.step} - Error finding element: {str(e)}", 2)
            return None
    
        if not isinstance(remains, (int, float)) or remains <= 0:
            self.output(f"Step {self.step} - Invalid 'remains' value: {remains}", 2)
            return None
    
        # Calculate max_clicks as 90% of the remaining clicks
        max_clicks = max(1, int(remains * 0.8))  # 80% of remains
        self.output(f"Step {self.step} - Setting max clicks to 90% of remains: {max_clicks}", 3)
    
        # Set batch size to 100 clicks per batch
        batch_size = 100
        total_clicks = 0
        # Increase the script timeout to 10 minutes (600 seconds)
        self.driver.set_script_timeout(600)
    
        while total_clicks < max_clicks and remains > 0:
            # Calculate the number of clicks for the current batch
            batch_clicks = min(batch_size, max_clicks - total_clicks)
    
            # Define the JavaScript function to simulate `batch_clicks` on the button
            click_script = f"""
            return new Promise((resolve) => {{
                let clicks = 0;
                const xPositions = [135, 150, 165];  // Cycle through these x positions

                function performClick() {{
                    const clickButton = document.getElementsByClassName('user-tap-button')[0];
                    if (clickButton && clicks < {batch_clicks}) {{
                        xPositions.forEach((xPos) => {{
                            // Random y position between 290 and 310
                            const randomY = Math.floor(Math.random() * 21) + 290;
                            const clickEvent1 = new PointerEvent('pointerdown', {{clientX: xPos, clientY: randomY}});
                            const clickEvent2 = new PointerEvent('pointerup', {{clientX: xPos, clientY: randomY}});
                            clickButton.dispatchEvent(clickEvent1);
                            clickButton.dispatchEvent(clickEvent2);
                        }});
                        clicks += 3;  // Increment by 3 after each set of clicks

                        // Random delay between 200 and 400 milliseconds for the next set of clicks
                        const randomDelay = Math.floor(Math.random() * 201) + 200;  
                        setTimeout(performClick, randomDelay);
                    }} else {{
                        console.log('Finished clicking: ' + clicks + ' times');
                        resolve(clicks);  // Resolve the Promise with the final click count for this batch
                    }}
                }}

                // Start the first set of clicks immediately
                performClick();
            }});
            """
    
            # Execute the JavaScript for the current batch and wait for completion
            try:
                batch_result = self.driver.execute_script(click_script)
                total_clicks += batch_result
                remains -= batch_result
    
                self.output(f"Step {self.step} - Completed {batch_result} clicks. Total: {total_clicks} clicks. {remains} remaining.", 2)
            except Exception as e:
                self.output(f"Step {self.step} - Error executing JS click function: {str(e)}", 2)
                return None
    
            # Check if we've reached the max clicks or remaining targets
            if total_clicks >= max_clicks or remains <= 0:
                break
    
            # Optional: Delay between batches to simulate human behavior
            time.sleep(random.uniform(0.2, 0.5))  # Short delay between batches
    
        self.output(f"Step {self.step} - Finished session with {total_clicks} clicks. {remains} targets remaining.", 2)

    def get_profit_hour(self, claimed=False):
        prefix = "After" if claimed else "Before"
        default_priority = 2 if claimed else 3

        priority = max(self.settings['verboseLevel'], default_priority)

        # Construct the specific profit XPath
        profit_text = f'{prefix} PROFIT/HOUR:'
        profit_xpath = "//div[@class='price-value']"

        try:
            element = self.strip_non_numeric(self.monitor_element(profit_xpath, 15, "get profit per hour"))

            # Check if element is not None and process the profit
            if element:
                self.output(f"Step {self.step} - {profit_text} {element}", priority)

        except NoSuchElementException:
            self.output(f"Step {self.step} - Element containing '{prefix} Profit/Hour:' was not found.", priority)
        except Exception as e:
            self.output(f"Step {self.step} - An error occurred: {str(e)}", priority)  # Provide error as string for logging
        
        self.increase_step()

def main():
    claimer = HamsterKombatClaimer()
    claimer.run()

if __name__ == "__main__":
    main()