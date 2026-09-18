"""Balance extraction, text cleanup and claim timing."""

import time
import re
import random
from selenium.webdriver.common.by import By
from selenium.common.exceptions import NoSuchElementException


class ClaimHelpersMixin:
    """Balance extraction, text cleanup and claim timing. Uses the shared state on Claimer."""

    def show_time(self, time):
        hours = int(time / 60)
        minutes = time % 60
        if hours > 0:
            hour_str = f"{hours} hour" if hours == 1 else f"{hours} hours"
            if minutes > 0:
                minute_str = f"{minutes} minute" if minutes == 1 else f"{minutes} minutes"
                return f"{hour_str} and {minute_str}"
            return hour_str
        minute_str = f"{minutes} minute" if minutes == 1 else f"{minutes} minutes"
        return minute_str

    def strip_html_and_non_numeric(self, text):
        """Remove HTML tags and keep only numeric characters and decimal points."""
        text = self.strip_html(text)
        text = self.strip_non_numeric(text)
        return text

    def strip_html(self, text):
        """Remove HTML tags."""
        clean = re.compile('<.*?>')
        return clean.sub('', text)

    def strip_non_numeric(self, text):
        """Keep only numeric characters and decimal points."""
        return re.sub(r'[^0-9.]', '', text)

    def apply_random_offset(self, unmodifiedTimer):
        # Helper function to format minutes into hours and minutes
        def format_time(minutes):
            hours = int(minutes) // 60
            mins = int(minutes) % 60
            time_parts = []
            if hours > 0:
                time_parts.append(f"{hours} hour{'s' if hours != 1 else ''}")
            if mins > 0 or hours == 0:
                time_parts.append(f"{mins} minute{'s' if mins != 1 else ''}")
            return ' '.join(time_parts)
    
        # Try to convert unmodifiedTimer to float, default to 60 on failure
        try:
            unmodifiedTimer = float(unmodifiedTimer)
        except Exception as e:
            self.output(
                f"Error converting unmodifiedTimer to float: {str(e)}. Defaulting to 60 minutes.",
                2
            )
            unmodifiedTimer = 60.0
    
        if self.allow_early_claim:
            if self.settings['lowestClaimOffset'] <= self.settings['highestClaimOffset']:
                low = self.settings['lowestClaimOffset']
                high = self.settings['highestClaimOffset']
                self.output(
                    f"Step {self.step} - Picking a random offset between {low} and {high} minutes.",
                    3
                )
                self.random_offset = random.randint(low, high)
                modifiedTimer = unmodifiedTimer + self.random_offset
                self.output(
                    f"Step {self.step} - Random offset applied the random offset of: {self.random_offset} minutes to original time of {unmodifiedTimer} minutes.",
                    3
                )
                self.output(
                    f"Step {self.step} - Returned modified timer: {modifiedTimer} minutes ({format_time(modifiedTimer)}).",
                    3
                )
                return int(modifiedTimer)
        else:
            if self.settings['lowestClaimOffset'] <= self.settings['highestClaimOffset']:
                # Original offsets
                original_low = self.settings['lowestClaimOffset']
                original_high = self.settings['highestClaimOffset']
                # Cap the offsets to at least 0
                capped_lowest = max(original_low, 0)
                capped_highest = max(original_high, 0)
                # Determine if capping occurred
                low_capped = capped_lowest != original_low
                high_capped = capped_highest != original_high
                # Prepare strings for outputs
                low_str = f"{capped_lowest}" + (" (capped)" if low_capped else "")
                high_str = f"{capped_highest}" + (" (capped)" if high_capped else "")
                self.output(
                    f"Step {self.step} - Picking a random offset between {low_str} and {high_str} minutes.",
                    3
                )
                if low_capped or high_capped:
                    self.output(
                        f"Step {self.step} - Offsets were capped to 0: lowestClaimOffset={low_str}, highestClaimOffset={high_str}",
                        3
                    )
                self.random_offset = random.randint(capped_lowest, capped_highest)
                modifiedTimer = unmodifiedTimer + self.random_offset
                self.output(
                    f"Step {self.step} - Random offset applied to the wait timer of: {self.random_offset} minutes ({format_time(self.random_offset)}).",
                    3
                )
                self.output(
                    f"Step {self.step} - Returned modified timer: {modifiedTimer} minutes ({format_time(modifiedTimer)}).",
                    3
                )
                return int(modifiedTimer)
        # If no conditions are met, return the original unmodifiedTimer
        return unmodifiedTimer

    def get_balance(self, balance_xpath, claimed=False):
        prefix = "After" if claimed else "Before"
        default_priority = 2 if claimed else 3
        priority = max(self.settings['verboseLevel'], default_priority)
        balance_text = f'{prefix} BALANCE:'
        
        try:
            # Move to the balance element
            # self.move_and_click(balance_xpath, 20, False, "move to the balance", self.step, "visible")
            monitor_result = self.monitor_element(balance_xpath, 15, "get balance")
            
            # Fallback if nothing was captured
            if not monitor_result:
                self.output(f"Step {self.step} - monitor_element returned nothing. Attempting fallback method for balance...", priority)
                try:
                    elements = self.driver.find_elements(By.XPATH, balance_xpath)
                    fallback_texts = []
                    for el in elements:
                        text = self.driver.execute_script("return arguments[0].textContent;", el).strip()
                        if text:
                            fallback_texts.append(text)
                    if fallback_texts:
                        monitor_result = " ".join(fallback_texts)
                    else:
                        monitor_result = False
                except Exception as fallback_e:
                    self.output(f"Step {self.step} - Fallback method failed: {fallback_e}", priority)
                    monitor_result = False

            if monitor_result is False:
                self.output(f"Step {self.step} - No balance text found. Restarting driver...", priority)
                self.quit_driver()
                self.launch_iframe()
                monitor_result = self.monitor_element(balance_xpath, 20, "get balance")
            
            # Clean and convert the result
            element = self.strip_html_and_non_numeric(monitor_result)
            if element:
                balance_float = round(float(element), 3)
                self.output(f"Step {self.step} - {balance_text} {balance_float}", priority)
                return balance_float
            else:
                self.output(f"Step {self.step} - {balance_text} not found or not numeric.", priority)
                return None
        except NoSuchElementException:
            self.output(f"Step {self.step} - Element containing '{prefix} Balance:' was not found.", priority)
            return None
        except Exception as e:
            self.output(f"Step {self.step} - An error occurred: {str(e)}", priority)
            return None
        finally:
            self.increase_step()

    def get_wait_time(self, wait_time_xpath, step_number="108", beforeAfter="pre-claim"):
        try:
            self.output(f"Step {self.step} - Get the wait time...", 3)
            
            # Move to the wait timer element and capture its text
            wait_time_text = self.monitor_element(wait_time_xpath, 20, "claim timer")
            
            # Fallback if nothing was captured
            if not wait_time_text:
                self.output(f"Step {self.step} - monitor_element returned nothing. Attempting fallback method for wait time...", 3)
                try:
                    elements = self.driver.find_elements(By.XPATH, wait_time_xpath)
                    fallback_texts = []
                    for el in elements:
                        text = self.driver.execute_script("return arguments[0].textContent;", el).strip()
                        if text:
                            fallback_texts.append(text)
                    if fallback_texts:
                        wait_time_text = " ".join(fallback_texts)
                    else:
                        wait_time_text = False
                except Exception as fallback_e:
                    self.output(f"Step {self.step} - Fallback method failed: {fallback_e}", 3)
                    wait_time_text = False
    
            if wait_time_text:
                wait_time_text = wait_time_text.strip()
                self.output(f"Step {self.step} - Extracted wait time text: '{wait_time_text}'", 3)
                
                # Updated patterns to ignore preceding text and to match explicit hour-minute format
                patterns = [
                    r".*?(\d+)h\s*(\d+)m(?:\s*(\d+)(?:s|d))?",
                    r".*?(\d{1,2}):(\d{2})(?::(\d{2}))?"
                ]
                
                total_minutes = None
                for pattern in patterns:
                    match = re.search(pattern, wait_time_text)
                    if match:
                        groups = match.groups()
                        total_minutes = 0.0
                        if len(groups) == 3:
                            hours, minutes, seconds = groups
                            if hours:
                                total_minutes += int(hours) * 60
                            if minutes:
                                total_minutes += int(minutes)
                            if seconds:
                                total_minutes += int(seconds) / 60.0
                            if not any([hours, minutes, seconds]):
                                total_minutes = None
                        # If matching colon separated pattern (hours and minutes, optional seconds)
                        elif len(groups) == 2:
                            hours, minutes = groups
                            if hours:
                                total_minutes += int(hours) * 60
                            if minutes:
                                total_minutes += int(minutes)
                        if total_minutes is not None:
                            break
                
                if total_minutes is not None and total_minutes > 0:
                    total_minutes = round(total_minutes, 1)
                    self.output(f"Step {self.step} - Total wait time in minutes: {total_minutes}", 3)
                    return total_minutes
                else:
                    self.output(f"Step {self.step} - Wait time pattern not matched in text: '{wait_time_text}'", 3)
                    return False
            else:
                self.output(f"Step {self.step} - No wait time text found.", 3)
                return False
        except Exception as e:
            self.output(f"Step {self.step} - An error occurred: {e}", 3)

            return False
