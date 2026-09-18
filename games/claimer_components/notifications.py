"""Console output, Telegram notifications and debug captures."""

import time
import re
import requests


class NotificationsMixin:
    """Console output, Telegram notifications and debug captures. Uses the shared state on Claimer."""

    def output(self, string, level=2):
        if self.settings['verboseLevel'] >= level:
            print(string)
        if self.settings['telegramBotToken'] and not self.settings['telegramBotChatId']:
            try:
                self.settings['telegramBotChatId'] = self.get_telegram_bot_chat_id()
                self.save_settings()  # Save the settings after getting the chat ID
            except ValueError as e:
                pass
                # print(f"Error fetching Telegram chat ID: {e}")
        if self.settings['telegramBotChatId'] and self.wallet_id and self.settings['telegramVerboseLevel'] >= level:
            self.send_message(string)

    def get_telegram_bot_chat_id(self):
        """
        Fetches the most recent update and returns its chat_id and message_id.
        Raises if no updates or no message object is found.
        """
        url = f"https://api.telegram.org/bot{self.settings['telegramBotToken']}/getUpdates"
        params = {
            "limit": 1,    # only the latest update
            "timeout": 0,  # no long-polling
        }
        data = requests.get(url, params=params).json()
        updates = data.get("result", [])
        if not updates:
            raise ValueError("No updates found. Ensure the bot has received at least one message.")
        
        latest = updates[-1]
        msg = latest.get("message") or latest.get("edited_message")
        if not msg:
            raise ValueError("Latest update contains no message object.")
        
        chat_id = msg["chat"]["id"]
        message_id = msg["message_id"]
        return chat_id

    def send_message(self, string):
        try:
            if self.settings['telegramBotChatId'] == "":
                self.settings['telegramBotChatId'] = self.get_telegram_bot_chat_id()

            message = f"{self.wallet_id}: {string}"
            url = f"https://api.telegram.org/bot{self.settings['telegramBotToken']}/sendMessage?chat_id={self.settings['telegramBotChatId']}&text={message}"
            response = requests.get(url).json()
            # print(response)  # This sends the message and prints the response (Commented out for cleaner output)
            if not response.get("ok"):
                raise ValueError(f"Failed to send message: {response}")
        except ValueError as e:
            print(f"Error: {e}")

    def debug_information(self, action_description, error_type="error"):
        # Use only the first line to avoid including a full stacktrace
        short_description = action_description.splitlines()[0]
    
        # Replace characters that might corrupt the intended filename structure
        sanitized_description = re.sub(r'[\/\0\\\*\?\:\|\<\>\"\&\;\$~ ]', '-', short_description)
    
        # Truncate the sanitized description to prevent exceeding max filename limits
        max_filename_length = 50  # adjust as needed
        sanitized_description = sanitized_description[:max_filename_length]
    
        # Take a screenshot if the element should have been present
        time.sleep(3)
        screenshot_path = f"{self.screenshots_path}/{self.step}_{sanitized_description}.png"
        self.driver.save_screenshot(screenshot_path)
    
        # Check if "not" is present in the action_description enclosed in brackets; if so, skip further debugging
        if re.search(r'\(.*?not.*?\)', action_description, re.IGNORECASE):
            return
    
        # Save the HTML page source on error
        if error_type == "error":
            page_source = self.driver.page_source
            page_source_path = f"{self.screenshots_path}/{self.step}_{sanitized_description}_page_source.html"
            with open(page_source_path, "w", encoding="utf-8") as f:
                f.write(page_source)
