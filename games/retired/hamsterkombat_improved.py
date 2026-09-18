"""
HamsterKombat Claimer - Improved Version
Type hints, error handling, and security improvements.
"""

import os
import sys
import time
import random
import re
from datetime import datetime
from typing import Optional, Tuple
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import NoSuchElementException, TimeoutException

from claimer_improved import Claimer, DEFAULT_TIMEOUT, ELEMENT_CLICK_TIMEOUT


class HamsterKombatClaimer(Claimer):
    """
    Automate HamsterKombat Telegram game claiming and tapping.
    """

    def initialize_settings(self) -> None:
        """Initialize game-specific settings."""
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

    def __init__(self) -> None:
        """Initialize the claimer."""
        self.settings_file = "variables.txt"
        self.status_file_path = "status.txt"
        self.wallet_id = ""
        self.load_settings()
        self.random_offset = random.randint(self.settings['lowestClaimOffset'], self.settings['highestClaimOffset'])
        super().__init__()

    def next_steps(self) -> None:
        """Execute next steps to launch the game."""
        if self.step:
            pass
        else:
            self.step = "01"

        try:
            self.launch_iframe()
            self.increase_step()
            self.set_cookies()
        except TimeoutException:
            self.output(f"Step {self.step} - Failed to find or switch to iframe within timeout period.", 1)
        except Exception as e:
            self.output(f"Step {self.step} - An error occurred: {e}", 1)

    def full_claim(self) -> int:
        """
        Execute the full claim process and return wait time.

        Returns:
            Wait time in minutes until next claim
        """
        self.step = "100"
        self.launch_iframe()

        # Try to claim daily reward
        xpath = "//button[span[text()='Claim']]"
        success = self.move_and_click(xpath, 20, True, "Daily Reward claim button", self.step, "clickable")
        self.increase_step()

        # Click "Thank you, Hamster"
        xpath = "//button[span[text()='Thank you, Hamster']]"
        success = self.move_and_click(xpath, 20, True, "'Thank you hamster' bonus", self.step, "clickable")
        self.increase_step()

        # Capture initial values
        initial_remains = self.get_remains()
        initial_balance = self.get_balance(claimed=False)

        if initial_balance is None:
            self.output(f"Step {self.step} - Failed to retrieve initial balance.", 2)

        self.output(f"Step {self.step} - Initial Remains: {initial_remains}, Initial Balance: {initial_balance}", 3)

        starting_clicks = initial_remains
        self.output(f"Step {self.step} - Starting clicks: {starting_clicks}", 3)

        if isinstance(starting_clicks, (int, float)) and starting_clicks > 0:
            self.click_ahoy(starting_clicks)

        remains_after_clicks = self.get_remains()

        if isinstance(remains_after_clicks, (int, float)):
            self.output(f"Step {self.step} - Remaining clicks: {remains_after_clicks}", 3)
        else:
            self.output(f"Step {self.step} - Unable to retrieve valid remains after clicks.", 3)

        self.get_profit_hour(claimed=True)
        final_balance = self.get_balance(claimed=True)

        if final_balance is None:
            self.output(f"Step {self.step} - Failed to retrieve final balance.", 2)

        # Calculate differences
        remains_diff = (
            initial_remains - remains_after_clicks
            if isinstance(initial_remains, (int, float)) and isinstance(remains_after_clicks, (int, float))
            else 0
        )
        balance_diff = (
            final_balance - initial_balance
            if isinstance(initial_balance, (int, float)) and isinstance(final_balance, (int, float))
            else 0
        )

        self.output(f"STATUS: We used {remains_diff} energy to gain {balance_diff} more tokens.", 1)

        random_timer = random.randint(20, 60)
        self.output(f"Step {self.step} - Recharging energy for {random_timer} minutes.", 3)
        return random_timer

    def get_balance(self, claimed: bool = False) -> Optional[float]:
        """
        Get current balance.

        Args:
            claimed: Whether balance is after claim

        Returns:
            Balance value or None if not found
        """
        prefix = "After" if claimed else "Before"
        default_priority = 2 if claimed else 3
        priority = max(self.settings['verboseLevel'], default_priority)

        balance_xpath = f"//div[@class='user-balance-large-inner']/p"

        try:
            element = self.monitor_element(balance_xpath, ELEMENT_CLICK_TIMEOUT, "get balance")

            if element:
                cleaned_balance = self.strip_html_and_non_numeric(element)
                self.output(f"Step {self.step} - {prefix} BALANCE: {cleaned_balance}", priority)
                return float(cleaned_balance)
        except NoSuchElementException:
            self.output(f"Step {self.step} - Element containing '{prefix} Balance:' was not found.", priority)
        except Exception as e:
            self.output(f"Step {self.step} - An error occurred: {str(e)}", priority)

        self.increase_step()
        return None

    def get_remains(self) -> Optional[int]:
        """
        Get remaining energy clicks.

        Returns:
            Remaining clicks or None if not found
        """
        remains_xpath = "//div[@class='user-tap-energy']/p"

        try:
            self.move_and_click(remains_xpath, ELEMENT_CLICK_TIMEOUT, False, "remove overlays", self.step, "visible")
            remains_element = self.monitor_element(remains_xpath, 15, "get remaining clicks")

            if remains_element:
                remains_text = remains_element.strip()
                if " / " in remains_text:
                    parts = remains_text.split(" / ")
                    n1, n2 = int(parts[0]), int(parts[1])
                    self.output(f"Step {self.step} - {n1} energy remaining of a maximum {n2}.", 3)
                    return n1
                else:
                    self.output(f"Step {self.step} - Unexpected format: '{remains_text}'", 3)
                    return None
            else:
                self.output(f"Step {self.step} - Element containing 'Remains' was not found.", 3)
                return None
        except NoSuchElementException:
            self.output(f"Step {self.step} - Element containing 'Remains' was not found.", 3)
            return None
        except Exception as e:
            self.output(f"Step {self.step} - An error occurred: {str(e)}", 3)
            return None

    def click_ahoy(self, remains: int) -> None:
        """
        Click energy button automatically.

        Args:
            remains: Number of clicks to perform (80% of remains)
        """
        xpath = "//div[@class='user-tap-energy']/p"
        self.move_and_click(xpath, ELEMENT_CLICK_TIMEOUT, False, "get closer to hamster!", self.step, "visible")

        self.output(f"Step {self.step} - We have {remains} targets to click. This might take some time!", 3)

        try:
            element = self.driver.find_element(By.XPATH, xpath)
        except Exception as e:
            self.output(f"Step {self.step} - Error finding element: {e}", 2)
            return

        if not isinstance(remains, (int, float)) or remains <= 0:
            self.output(f"Step {self.step} - Invalid 'remains' value: {remains}", 2)
            return

        # Calculate max clicks (80% of remains)
        max_clicks = max(1, int(remains * 0.8))
        self.output(f"Step {self.step} - Setting max clicks to 90% of remains: {max_clicks}", 3)

        batch_size = 100
        total_clicks = 0
        self.driver.set_script_timeout(600)

        while total_clicks < max_clicks and remains > 0:
            batch_clicks = min(batch_size, max_clicks - total_clicks)

            click_script = f"""
            return new Promise((resolve) => {{
                let clicks = 0;
                const xPositions = [135, 150, 165];

                function performClick() {{
                    const clickButton = document.getElementsByClassName('user-tap-button')[0];
                    if (clickButton && clicks < {batch_clicks}) {{
                        xPositions.forEach((xPos) => {{
                            const randomY = Math.floor(Math.random() * 21) + 290;
                            const clickEvent1 = new PointerEvent('pointerdown', {{clientX: xPos, clientY: randomY}});
                            const clickEvent2 = new PointerEvent('pointerup', {{clientX: xPos, clientY: randomY}});
                            clickButton.dispatchEvent(clickEvent1);
                            clickButton.dispatchEvent(clickEvent2);
                        }});
                        clicks += 3;

                        const randomDelay = Math.floor(Math.random() * 201) + 200;
                        setTimeout(performClick, randomDelay);
                    }} else {{
                        console.log('Finished clicking: ' + clicks + ' times');
                        resolve(clicks);
                    }}
                }}

                performClick();
            }});
            """

            try:
                batch_result = self.driver.execute_script(click_script)
                total_clicks += batch_result
                remains -= batch_result
                self.output(f"Step {self.step} - Completed {batch_result} clicks. Total: {total_clicks} clicks. {remains} remaining.", 2)
            except Exception as e:
                self.output(f"Step {self.step} - Error executing JS click function: {e}", 2)
                return

            if total_clicks >= max_clicks or remains <= 0:
                break

            time.sleep(random.uniform(0.2, 0.5))

        self.output(f"Step {self.step} - Finished session with {total_clicks} clicks. {remains} targets remaining.", 2)

    def get_profit_hour(self, claimed: bool = False) -> None:
        """
        Get profit per hour.

        Args:
            claimed: Whether to get profit after claim
        """
        prefix = "After" if claimed else "Before"
        default_priority = 2 if claimed else 3
        priority = max(self.settings['verboseLevel'], default_priority)

        profit_xpath = "//div[@class='price-value']"

        try:
            element = self.strip_non_numeric(self.monitor_element(profit_xpath, 15, "get profit per hour"))

            if element:
                self.output(f"Step {self.step} - {prefix} PROFIT/HOUR: {element}", priority)
        except NoSuchElementException:
            self.output(f"Step {self.step} - Element containing '{prefix} Profit/Hour:' was not found.", priority)
        except Exception as e:
            self.output(f"Step {self.step} - An error occurred: {str(e)}", priority)

        self.increase_step()


def main() -> None:
    """Main entry point."""
    claimer = HamsterKombatClaimer()
    claimer.run()


if __name__ == "__main__":
    main()
