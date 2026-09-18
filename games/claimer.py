"""Public claimer entry point and claim lifecycle.

Game bots keep using ``from claimer import Claimer``. Supporting methods live
in claimer_components and operate on this same instance, preserving overrides.
"""

import os
import shutil
import sys
import time
import json
import random
from datetime import datetime, timedelta
import requests

from claimer_components.settings import SettingsMixin
from claimer_components.notifications import NotificationsMixin
from claimer_components.browser import BrowserMixin
from claimer_components.sessions import SessionsMixin
from claimer_components.telegram import TelegramMixin
from claimer_components.webapp import WebAppMixin
from claimer_components.interactions import InteractionsMixin
from claimer_components.click_strategies import ClickStrategiesMixin
from claimer_components.wallet import WalletMixin
from claimer_components.claim_helpers import ClaimHelpersMixin


class Claimer(
    SettingsMixin,
    NotificationsMixin,
    BrowserMixin,
    SessionsMixin,
    TelegramMixin,
    WebAppMixin,
    InteractionsMixin,
    ClickStrategiesMixin,
    WalletMixin,
    ClaimHelpersMixin,
):
    """Shared bot lifecycle composed from focused, state-sharing capabilities."""

    # Preserve the original class attribute for existing callers.
    requests = requests

    def __init__(self):
        self.initialize_settings()
        self.load_settings()
        self.random_offset = random.randint(self.settings['lowestClaimOffset'], self.settings['highestClaimOffset'])
        print(f"Initialising the {self.prefix} Wallet Auto-claim Python Script - Good Luck!")

        self.imported_seedphrase = None

        # Update the settings based on user input
        if len(sys.argv) > 1:
            user_input = sys.argv[1]  # Get session ID from command-line argument
            self.wallet_id = user_input
            self.output(f"Session ID provided: {user_input}", 2)
            
            # Safely check for a second argument
            if len(sys.argv) > 2 and sys.argv[2] == "reset":
                self.settings['forceNewSession'] = True

            # Check for the --seed-phrase flag and validate it
            if '--seed-phrase' in sys.argv:
                seed_index = sys.argv.index('--seed-phrase') + 1
                if seed_index < len(sys.argv):
                    self.seed_phrase = ' '.join(sys.argv[seed_index:])
                    seed_words = self.seed_phrase.split()
                    if len(seed_words) == 12:
                        self.output(f"Seed phrase accepted:", 2)
                        self.imported_seedphrase = self.seed_phrase
                    else:
                        self.output("Invalid seed phrase. Ignoring.", 2)
                else:
                    self.output("No seed phrase provided after --seed-phrase flag. Ignoring.", 2)
        else:
            self.output("\nCurrent settings:", 1)
            for key, value in self.settings.items():
                self.output(f"{key}: {value}", 1)
            user_input = input("\nShould we update our settings? (Default:<enter> / Yes = y): ").strip().lower()
            if user_input == "y":
                self.update_settings()
            user_input = self.get_session_id()
            self.wallet_id = user_input

        self.session_path = f"./selenium/{self.wallet_id}"
        os.makedirs(self.session_path, exist_ok=True)
        self.screenshots_path = f"./screenshots/{self.wallet_id}"
        os.makedirs(self.screenshots_path, exist_ok=True)
        self.backup_path = f"./backups/{self.wallet_id}"
        os.makedirs(self.backup_path, exist_ok=True)
        self.step = "01"

        # Define our base path for debugging screenshots
        self.screenshot_base = os.path.join(self.screenshots_path, "screenshot")

        if self.settings["useProxy"] and self.settings["proxyAddress"] == "http://127.0.0.1:8080":
            self.run_http_proxy()
        elif self.forceLocalProxy:
            self.run_http_proxy()
            self.output("Use of the built-in proxy is forced on for this game.", 2)
        else:
            self.output("Proxy disabled in settings.", 2)

    def initialize_settings(self):
        self.settings_file = "variables.txt"
        self.status_file_path = "status.txt"
        self.start_app_xpath = None
        self.settings = {}
        self.driver = None
        self.target_element = None
        self.random_offset = 0
        self.seed_phrase = None
        self.wallet_id = ""
        self.script = "default_script.py"
        self.prefix = "Default:"
        self.allow_early_claim = True
        self.default_platform = "web"

    def run(self):
        if not self.settings["forceNewSession"]:
            self.load_settings()
        cookies_path = os.path.join(self.session_path, 'cookies.json')
        if os.path.exists(cookies_path) and not self.settings['forceNewSession']:
            self.output("Resuming the previous session...", 2)
        else:
            telegram_backup_dirs = [d for d in os.listdir(os.path.dirname(self.session_path)) if d.startswith("Telegram")]
            if telegram_backup_dirs:
                print("Previous Telegram login sessions found. Pressing <enter> will select the account numbered '1':")
                for i, dir_name in enumerate(telegram_backup_dirs):
                    print(f"{i + 1}. {dir_name}")

                user_input = input("Enter the number of the session you want to restore, or 'n' to create a new session: ").strip().lower()

                if user_input == 'n':
                    self.log_into_telegram(self.wallet_id)
                    self.quit_driver()
                    self.backup_telegram()
                elif user_input.isdigit() and 0 < int(user_input) <= len(telegram_backup_dirs):
                    self.restore_from_backup(os.path.join(os.path.dirname(self.session_path), telegram_backup_dirs[int(user_input) - 1]))
                else:
                    self.restore_from_backup(os.path.join(os.path.dirname(self.session_path), telegram_backup_dirs[0]))  # Default to the first session

            else:
                self.log_into_telegram(self.wallet_id)
                self.quit_driver()
                self.backup_telegram()

            self.next_steps()
            self.quit_driver()

            try:
                shutil.copytree(self.session_path, self.backup_path, dirs_exist_ok=True)
                self.output("We backed up the session data in case of a later crash!", 3)
            except Exception as e:
                self.output(f"Oops, we weren't able to make a backup of the session data! Error: {e}", 1)

            pm2_session = self.session_path.replace("./selenium/", "")
            self.output(f"You could add the new/updated session to PM use: pm2 start {self.script} --interpreter venv/bin/python3 --name {pm2_session} -- {pm2_session}", 1)
            user_choice = input("Enter 'y' to continue to 'claim' function, 'e' to exit, 'a' or <enter> to automatically add to PM2: ").lower()

            if user_choice == "e":
                self.output("Exiting script. You can resume the process later.", 1)
                sys.exit()
            elif user_choice == "a" or not user_choice:
                self.start_pm2_app(self.script, pm2_session, pm2_session)
                user_choice = input("Should we save your PM2 processes? (Y/n): ").lower()
                if user_choice == "y" or not user_choice:
                    self.save_pm2()
                self.output(f"You can now watch the session log into PM2 with: pm2 logs {pm2_session}", 2)
                sys.exit()

        while True:
            self.manage_session()
            wait_time = self.full_claim()

            if os.path.exists(self.status_file_path):
                with open(self.status_file_path, "r+") as file:
                    status = json.load(file)
                    if self.session_path in status:
                        del status[self.session_path]
                        file.seek(0)
                        json.dump(status, file)
                        file.truncate()
                        self.output(f"Session released: {self.session_path}", 3)

            self.quit_driver()

            now = datetime.now()
            # Check if wait_time is not a number, assume 30
            if not isinstance(wait_time, (int, float)):
                wait_time = 30
            next_claim_time = now + timedelta(minutes=wait_time)
            this_claim_str = now.strftime("%d %B - %H:%M")
            next_claim_time_str = next_claim_time.strftime("%d %B - %H:%M")
            self.output(f"{this_claim_str} | Need to wait until {next_claim_time_str} before the next claim attempt. Approximately {wait_time} minutes.", 1)
            if self.settings["forceClaim"]:
                self.settings["forceClaim"] = False

            while wait_time > 0:
                this_wait = min(wait_time, 15)
                now = datetime.now()
                timestamp = now.strftime("%H:%M")
                self.output(f"[{timestamp}] Waiting for {this_wait} more minutes...", 3)
                time.sleep(this_wait * 60)  # Convert minutes to seconds
                wait_time -= this_wait
                if wait_time > 0:
                    self.output(f"Updated wait time: {wait_time} minutes left.", 3)

    def next_steps(self):
        # Must OVERRIDE this function in the child class
        self.output("Function 'next-steps' - Not defined (Need override in child class) \n", 1)

    def full_claim(self):
        # Must OVERRIDE this function in the child class
        self.output("Function 'full_claim' - Not defined (Need override in child class) \n", 1)

    def increase_step(self):
        step_int = int(self.step) + 1
        self.step = f"{step_int:02}"
