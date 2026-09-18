"""Settings persistence and interactive configuration."""

import os
import json


class SettingsMixin:
    """Settings persistence and interactive configuration. Uses the shared state on Claimer."""

    def load_settings(self):
        default_settings = {
            "forceClaim": False,
            "debugIsOn": True,
            "hideSensitiveInput": True,
            "screenshotQRCode": True,
            "maxSessions": 1,
            "verboseLevel": 2,
            "telegramVerboseLevel": 0,
            "lowestClaimOffset": 0,
            "highestClaimOffset": 15,
            "forceNewSession": False,
            "useProxy": False,
            "proxyAddress": "http://127.0.0.1:8080",
            "requestUserAgent": False,
            "telegramBotToken": "", 
            "telegramBotChatId": "",
            "enableCache": True  # New setting added here
        }

        if os.path.exists(self.settings_file):
            with open(self.settings_file, "r") as f:
                loaded_settings = json.load(f)
            # Filter out unused settings from previous versions
            self.settings = {k: loaded_settings.get(k, v) for k, v in default_settings.items()}
            self.output("Settings loaded successfully.", 3)
        else:
            self.settings = default_settings
            self.save_settings()

    def save_settings(self):
        with open(self.settings_file, "w") as f:
            json.dump(self.settings, f)
        self.output("Settings saved successfully.", 3)

    def update_settings(self):
        
        def update_setting(setting_key, message):
            current_value = self.settings.get(setting_key)
            response = input(f"\n{message} (Y/N, press Enter to keep current [{current_value}]): ").strip().lower()
            if response == "y":
                self.settings[setting_key] = True
            elif response == "n":
                self.settings[setting_key] = False
            else:
                print(f"Keeping current setting: {current_value}")

        update_setting("forceClaim", "Shall we force a claim on first run? Does not wait for the timer to be filled")
        update_setting("debugIsOn", "Should we enable debugging? This will save screenshots in your local drive")
        update_setting("hideSensitiveInput", "Should we hide sensitive input? Your phone number and seed phrase will not be visible on the screen")
        update_setting("screenshotQRCode", "Shall we allow log in by QR code? The alternative is by phone number and one-time password")

        try:
            new_max_sessions = int(input(f"\nEnter the number of max concurrent claim sessions. Additional claims will queue until a session slot is free.\n(current: {self.settings['maxSessions']}): "))
            self.settings["maxSessions"] = new_max_sessions
        except ValueError:
            self.output("Number of sessions remains unchanged.", 1)

        try:
            new_verbose_level = int(input("\nEnter the number for how much information you want displaying in the console.\n 3 = all messages, 2 = claim steps, 1 = minimal steps\n(current: {}): ".format(self.settings['verboseLevel'])))
            if 1 <= new_verbose_level <= 3:
                self.settings["verboseLevel"] = new_verbose_level
                self.output("Verbose level updated successfully.", 2)
            else:
                self.output("Verbose level remains unchanged.", 2)
        except ValueError:
            self.output("Verbose level remains unchanged.", 2)

        try:
            new_telegram_verbose_level = int(input("\nEnter the Telegram verbose level (3 = all messages, 2 = claim steps, 1 = minimal steps)\n(current: {}): ".format(self.settings['telegramVerboseLevel'])))
            if 0 <= new_telegram_verbose_level <= 3:
                self.settings["telegramVerboseLevel"] = new_telegram_verbose_level
                self.output("Telegram verbose level updated successfully.", 2)
            else:
                self.output("Telegram verbose level remains unchanged.", 2)
        except ValueError:
            self.output("Telegram verbose level remains unchanged.", 2)

        try:
            new_lowest_offset = int(input("\nEnter the lowest possible offset for the claim timer (valid values are -30 to +30 minutes)\n(current: {}): ".format(self.settings['lowestClaimOffset'])))
            if -30 <= new_lowest_offset <= 30:
                self.settings["lowestClaimOffset"] = new_lowest_offset
                self.output("Lowest claim offset updated successfully.", 2)
            else:
                self.output("Invalid range for lowest claim offset. Please enter a value between -30 and +30.", 2)
        except ValueError:
            self.output("Lowest claim offset remains unchanged.", 2)

        try:
            new_highest_offset = int(input("\nEnter the highest possible offset for the claim timer (valid values are 0 to 60 minutes)\n(current: {}): ".format(self.settings['highestClaimOffset'])))
            if 0 <= new_highest_offset <= 60:
                self.settings["highestClaimOffset"] = new_highest_offset
                self.output("Highest claim offset updated successfully.", 2)
            else:
                self.output("Invalid range for highest claim offset. Please enter a value between 0 and 60.", 2)
        except ValueError:
            self.output("Highest claim offset remains unchanged.", 2)

        if self.settings["lowestClaimOffset"] > self.settings["highestClaimOffset"]:
            self.settings["lowestClaimOffset"] = self.settings["highestClaimOffset"]
            self.output("Adjusted lowest claim offset to match the highest as it was greater.", 2)

        update_setting("useProxy", "Use Proxy?")
        update_setting("requestUserAgent", "Shall we collect a User Agent during setup?")
        
        # Collect the Telegram Bot Token
        new_telegram_bot_token = input(f"\nEnter the Telegram Bot Token (current: {self.settings['telegramBotToken']}): ").strip()
        if new_telegram_bot_token:
            self.settings["telegramBotToken"] = new_telegram_bot_token

        update_setting("enableCache", "Enable application cache?")

        self.save_settings()

        update_setting("forceNewSession", "Overwrite existing session and Force New Login? Use this if your saved session has crashed\nOne-Time only (setting not saved): ")

        self.output("\nRevised settings:", 1)
        for key, value in self.settings.items():
            self.output(f"{key}: {value}", 1)
        self.output("", 1)
