"""Session naming, slot locking, backups and PM2 processes."""

import os
import shutil
import time
import json
import random
import subprocess
from fcntl import flock, LOCK_EX, LOCK_UN
from selenium.webdriver.support.ui import WebDriverWait


class SessionsMixin:
    """Session naming, slot locking, backups and PM2 processes. Uses the shared state on Claimer."""

    def get_session_id(self):
        """Prompts the user for a session ID or determines the next sequential ID based on a 'Wallet' prefix.

        Returns:
            str: The entered session ID or the automatically generated sequential ID.
        """
        self.output(f"Your session will be prefixed with: {self.prefix}", 1)
        user_input = input("Enter your unique Session Name here, or hit <enter> for the next sequential wallet: ").strip()

        # Set the directory where session folders are stored
        screenshots_dir = "./screenshots/"

        # Ensure the directory exists to avoid FileNotFoundError
        if not os.path.exists(screenshots_dir):
            os.makedirs(screenshots_dir)

        # List contents of the directory
        try:
            dir_contents = os.listdir(screenshots_dir)
        except Exception as e:
            self.output(f"Error accessing the directory: {e}", 1)
            return None  # or handle the error differently

        # Filter directories with the 'Wallet' prefix and extract the numeric parts
        wallet_dirs = [int(dir_name.replace(self.prefix + 'Wallet', ''))
                    for dir_name in dir_contents
                    if dir_name.startswith(self.prefix + 'Wallet') and dir_name[len(self.prefix) + 6:].isdigit()]

        # Calculate the next wallet ID
        next_wallet_id = max(wallet_dirs) + 1 if wallet_dirs else 1

        # Use the next sequential wallet ID if no user input was provided
        if not user_input:
            user_input = f"Wallet{next_wallet_id}"  # Ensuring the full ID is prefixed correctly

        return self.prefix+user_input

    def manage_session(self):
        current_session = self.session_path
        current_timestamp = int(time.time())
        session_started = False
        new_message = True
        output_priority = 2

        while True:
            try:
                with open(self.status_file_path, "r+") as file:
                    flock(file, LOCK_EX)
                    status = json.load(file)

                    # Clean up expired sessions
                    for session_id, timestamp in list(status.items()):
                        if current_timestamp - timestamp > 300:  # 5 minutes
                            del status[session_id]
                            self.output(f"Removed expired session: {session_id}", 3)

                    # Check for available slots, exclude current session from count
                    active_sessions = {k: v for k, v in status.items() if k != current_session}
                    if len(active_sessions) < self.settings['maxSessions']:
                        status[current_session] = current_timestamp
                        file.seek(0)
                        json.dump(status, file)
                        file.truncate()
                        self.output(f"Session started: {current_session} in {self.status_file_path}", 3)
                        flock(file, LOCK_UN)
                        session_started = True
                        break
                    flock(file, LOCK_UN)

                if not session_started:
                    self.output(f"Waiting for slot. Current sessions: {len(active_sessions)}/{self.settings['maxSessions']}", output_priority)
                    if new_message:
                        new_message = False
                        output_priority = 3
                    time.sleep(random.randint(5, 15))
                else:
                    break

            except FileNotFoundError:
                # Create file if it doesn't exist
                with open(self.status_file_path, "w") as file:
                    flock(file, LOCK_EX)
                    json.dump({}, file)
                    flock(file, LOCK_UN)
            except json.decoder.JSONDecodeError:
                # Handle empty or corrupt JSON
                with open(self.status_file_path, "w") as file:
                    flock(file, LOCK_EX)
                    self.output("Corrupted status file. Resetting...", 3)
                    json.dump({}, file)
                    flock(file, LOCK_UN)

    def release_session(self):
        current_session = self.session_path
        current_timestamp = int(time.time())

        with open(self.status_file_path, "r+") as file:
            flock(file, LOCK_EX)
            status = json.load(file)
            if current_session in status:
                del status[current_session]
                file.seek(0)
                json.dump(status, file)
                file.truncate()
            flock(file, LOCK_UN)
            self.output(f"Session released: {current_session}", 3)

    def restore_from_backup(self, path):
        if os.path.exists(path):
            try:
                self.quit_driver()
                shutil.rmtree(self.session_path)
                shutil.copytree(path, self.session_path, dirs_exist_ok=True)
                self.driver = self.get_driver()
                self.driver.get(self.url)
                WebDriverWait(self.driver, 10).until(lambda d: d.execute_script('return document.readyState') == 'complete')
                self.output(f"Step {self.step} - Backup restored successfully.",2)
                return True
            except Exception as e:
                self.output(f"Step {self.step} - Error restoring backup: {e}\n",1)
                return False
        else:
            self.output(f"Step {self.step} - Backup directory does not exist.\n",1)
            return False

    def backup_telegram(self):

        # Ask the user if they want to backup their Telegram directory
        backup_prompt = input("Would you like to backup your Telegram directory? (Y/n): ").strip().lower()
        if backup_prompt == 'n':
            self.output(f"Step {self.step} - Backup skipped by user choice.", 3)
            return

        # Ask the user for a custom filename
        custom_filename = input("Enter a custom filename for the backup (leave blank for default): ").strip()

        # Define the backup destination path
        if custom_filename:
            backup_directory = os.path.join(os.path.dirname(self.session_path), f"Telegram:{custom_filename}")
        else:
            backup_directory = os.path.join(os.path.dirname(self.session_path), "Telegram")

        try:
            # Ensure the backup directory exists and copy the contents
            if not os.path.exists(backup_directory):
                os.makedirs(backup_directory)
            shutil.copytree(self.session_path, backup_directory, dirs_exist_ok=True)
            self.output(f"Step {self.step} - We backed up the session data in case of a later crash!", 3)
        except Exception as e:
            self.output(f"Step {self.step} - Oops, we weren't able to make a backup of the session data! Error: {e}", 1)

    def start_pm2_app(self, script_path, app_name, session_name):
        interpreter_path = "venv/bin/python3"
        command = f"NODE_NO_WARNINGS=1 pm2 start {script_path} --name {app_name} --interpreter {interpreter_path} --watch {script_path} -- {session_name}"
        subprocess.run(command, shell=True, check=True)

    def save_pm2(self):
        command = f"NODE_NO_WARNINGS=1 pm2 save"
        result = subprocess.run(command, shell=True, text=True, capture_output=True)
        print(result.stdout)
