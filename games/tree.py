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

def load_settings():
    global settings, settings_file
    # Default settings with all necessary keys
    default_settings = {
        "forceClaim": False,
        "debugIsOn": False,
        "hideSensitiveInput": True,
        "screenshotQRCode": True,
        "maxSessions": 1,
        "verboseLevel": 2,
        "lowestClaimOffset": 0,
        "highestClaimOffset": 15,
        "forceNewSession": False,
        "useProxy": False,
        "proxyAddress": "http://127.0.0.1:8080",
        "proxyUsername": "",
        "proxyPassword": ""
    }

    if os.path.exists(settings_file):
        with open(settings_file, "r") as f:
            loaded_settings = json.load(f)
        # Update default settings with any settings loaded from the file
        settings = {**default_settings, **loaded_settings}
        output("Settings loaded successfully.", 3)
    else:
        settings = default_settings
        save_settings()  # Save the default settings if the file does not exist

def save_settings():
    global settings, settings_file
    with open(settings_file, "w") as f:
        json.dump(settings, f)
    output("Settings saved successfully.", 3)

def output(string, level):
    if settings['verboseLevel'] >= level:
        print(string)

# Define sessions and settings files
settings_file = "variables.txt"
status_file_path = "status.txt"
settings = {}
load_settings()
driver = None
target_element = None
random_offset = random.randint(settings['lowestClaimOffset'], settings['highestClaimOffset'])
script = "games/tree.py"
prefix = "Tree:"
url = "https://www.treemine.app/login"
pot_full = "0h 0m to fill"
pot_filling = "to fill"

def increase_step():
    global step
    step_int = int(step) + 1
    step = f"{step_int:02}"

print(f"Initialising the {prefix} Wallet Auto-claim Python Script - Good Luck!")

def update_settings():
    global settings

    def update_setting(setting_key, message, default_value):
        current_value = settings.get(setting_key, default_value)
        response = input(f"\n{message} (Y/N, press Enter to keep current [{current_value}]): ").strip().lower()
        if response == "y":
            settings[setting_key] = True
        elif response == "n":
            settings[setting_key] = False

    update_setting("forceClaim", "Shall we force a claim on first run? Does not wait for the timer to be filled", settings["forceClaim"])
    update_setting("debugIsOn", "Should we enable debugging? This will save screenshots in your local drive", settings["debugIsOn"])
    update_setting("hideSensitiveInput", "Should we hide sensitive input? Your phone number and seed phrase will not be visible on the screen", settings["hideSensitiveInput"])
    update_setting("screenshotQRCode", "Shall we allow log in by QR code? The alternative is by phone number and one-time password", settings["screenshotQRCode"])

    try:
        new_max_sessions = int(input(f"\nEnter the number of max concurrent claim sessions. Additional claims will queue until a session slot is free.\n(current: {settings['maxSessions']}): "))
        settings["maxSessions"] = new_max_sessions
    except ValueError:
        output("Number of sessions remains unchanged.", 1)

    try:
        new_verbose_level = int(input("\nEnter the number for how much information you want displaying in the console.\n 3 = all messages, 2 = claim steps, 1 = minimal steps\n(current: {}): ".format(settings['verboseLevel'])))
        if 1 <= new_verbose_level <= 3:
            settings["verboseLevel"] = new_verbose_level
            output("Verbose level updated successfully.", 2)
        else:
            output("Verbose level remains unchanged.", 2)
    except ValueError:
        output("Verbose level remains unchanged.", 2)

    try:
        new_lowest_offset = int(input("\nEnter the lowest possible offset for the claim timer (valid values are -30 to +30 minutes)\n(current: {}): ".format(settings['lowestClaimOffset'])))
        if -30 <= new_lowest_offset <= 30:
            settings["lowestClaimOffset"] = new_lowest_offset
            output("Lowest claim offset updated successfully.", 2)
        else:
            output("Invalid range for lowest claim offset. Please enter a value between -30 and +30.", 2)
    except ValueError:
        output("Lowest claim offset remains unchanged.", 2)

    try:
        new_highest_offset = int(input("\nEnter the highest possible offset for the claim timer (valid values are 0 to 60 minutes)\n(current: {}): ".format(settings['highestClaimOffset'])))
        if 0 <= new_highest_offset <= 60:
            settings["highestClaimOffset"] = new_highest_offset
            output("Highest claim offset updated successfully.", 2)
        else:
            output("Invalid range for highest claim offset. Please enter a value between 0 and 60.", 2)
    except ValueError:
        output("Highest claim offset remains unchanged.", 2)

    if settings["lowestClaimOffset"] > settings["highestClaimOffset"]:
        settings["lowestClaimOffset"] = settings["highestClaimOffset"]
        output("Adjusted lowest claim offset to match the highest as it was greater.", 2)

    update_setting("useProxy", "Use Proxy?", settings["useProxy"])

    if settings["useProxy"]:
        proxy_address = input(f"\nEnter the Proxy IP address and port (current: {settings['proxyAddress']}): ").strip()
        if proxy_address:
            settings["proxyAddress"] = proxy_address

        proxy_username = input(f"\nEnter the Proxy username (current: {settings['proxyUsername']}): ").strip()
        if proxy_username:
            settings["proxyUsername"] = proxy_username

        proxy_password = input(f"\nEnter the Proxy password (current: {settings['proxyPassword']}): ").strip()
        if proxy_password:
            settings["proxyPassword"] = proxy_password

    save_settings()

    update_setting("forceNewSession", "Overwrite existing session and Force New Login? Use this if your saved session has crashed\nOne-Time only (setting not saved): ", settings["forceNewSession"])

    output("\nRevised settings:", 1)
    for key, value in settings.items():
        output(f"{key}: {value}", 1)
    output("", 1)

def get_session_id():
    """Prompts the user for a session ID or determines the next sequential ID based on a 'Wallet' prefix.

    Returns:
        str: The entered session ID or the automatically generated sequential ID.
    """
    global settings, prefix
    output(f"Your session will be prefixed with: {prefix}", 1)
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
        output(f"Error accessing the directory: {e}", 1)
        return None  # or handle the error differently

    # Filter directories with the 'Wallet' prefix and extract the numeric parts
    wallet_dirs = [int(dir_name.replace(prefix + 'Wallet', ''))
                   for dir_name in dir_contents
                   if dir_name.startswith(prefix + 'Wallet') and dir_name[len(prefix) + 6:].isdigit()]

    # Calculate the next wallet ID
    next_wallet_id = max(wallet_dirs) + 1 if wallet_dirs else 1

    # Use the next sequential wallet ID if no user input was provided
    if not user_input:
        user_input = f"Wallet{next_wallet_id}"  # Ensuring the full ID is prefixed correctly

    return prefix+user_input


imported_seedphrase = None
# Update the settings based on user input
if len(sys.argv) > 1:
    user_input = sys.argv[1]  # Get session ID from command-line argument
    output(f"Session ID provided: {user_input}", 2)
    
    # Safely check for a second argument
    if len(sys.argv) > 2 and sys.argv[2] == "reset":
        settings['forceNewSession'] = True

    # Check for the --seed-phrase flag and validate it
    if '--seed-phrase' in sys.argv:
        seed_index = sys.argv.index('--seed-phrase') + 1
        if seed_index < len(sys.argv):
            seed_phrase = ' '.join(sys.argv[seed_index:])
            seed_words = seed_phrase.split()
            if len(seed_words) == 12:
                output(f"Seed phrase accepted:", 2)
                imported_seedphrase = seed_phrase
            else:
                output("Invalid seed phrase. Ignoring.", 2)
        else:
            output("No seed phrase provided after --seed-phrase flag. Ignoring.", 2)
else:
    output("\nCurrent settings:", 1)
    for key, value in settings.items():
        output(f"{key}: {value}", 1)
    user_input = input("\nShould we update our settings? (Default:<enter> / Yes = y): ").strip().lower()
    if user_input == "y":
        update_settings()
    user_input = get_session_id()

session_path = "./selenium/{}".format(user_input)
os.makedirs(session_path, exist_ok=True)
screenshots_path = "./screenshots/{}".format(user_input)
os.makedirs(screenshots_path, exist_ok=True)
backup_path = "./backups/{}".format(user_input)
os.makedirs(backup_path, exist_ok=True)
step = "01"

# Define our base path for debugging screenshots
screenshot_base = os.path.join(screenshots_path, "screenshot")

def setup_driver():
    chrome_options = Options()
    chrome_options.add_argument(f"user-data-dir={session_path}")
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    user_agent = "Mozilla/5.0 (iPhone; CPU iPhone OS 17_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) EdgiOS/124.0.2478.50 Version/17.0 Mobile/15E148 Safari/604.1"
    chrome_options.add_argument(f"user-agent={user_agent}")

    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    chrome_options.add_experimental_option('useAutomationExtension', False)

    if settings["useProxy"]:
        proxy_server = settings["proxyAddress"]
        chrome_options.add_argument(f"--proxy-server={proxy_server}")

        if settings["proxyUsername"] and settings["proxyPassword"]:
            # Create a proxy authentication extension
            proxy_auth_plugin_path = create_proxyauth_extension(
                proxy_host=settings["proxyAddress"].split(':')[1][2:],
                proxy_port=settings["proxyAddress"].split(':')[2],
                proxy_username=settings["proxyUsername"],
                proxy_password=settings["proxyPassword"]
            )
            chrome_options.add_extension(proxy_auth_plugin_path)

    chrome_options.add_argument("--ignore-certificate-errors")
    chrome_options.add_argument("--allow-running-insecure-content")
    chrome_options.add_argument("--test-type")

    chromedriver_path = shutil.which("chromedriver")
    if chromedriver_path is None:
        output("ChromeDriver not found in PATH. Please ensure it is installed.", 1)
        exit(1)

    try:
        service = Service(chromedriver_path)
        driver = webdriver.Chrome(service=service, options=chrome_options)
        return driver
    except Exception as e:
        output(f"Initial ChromeDriver setup may have failed: {e}", 1)
        output("Please ensure you have the correct ChromeDriver version for your system.", 1)
        exit(1)

def run_http_proxy():
    proxy_lock_file = "./start_proxy.txt"
    max_wait_time = 15 * 60  # 15 minutes
    wait_interval = 5  # 5 seconds
    start_time = time.time()

    while os.path.exists(proxy_lock_file) and (time.time() - start_time) < max_wait_time:
        output("Proxy is already running. Waiting for it to free up...", 1)
        time.sleep(wait_interval)

    if os.path.exists(proxy_lock_file):
        output("Max wait time elapsed. Proceeding to run the proxy.", 1)

    with open(proxy_lock_file, "w") as lock_file:
        lock_file.write(f"Proxy started at: {time.ctime()}\n")

    try:
        subprocess.run(['./launch.sh', 'enable-proxy'], check=True)
        output("http-proxy started successfully.", 1)
    except subprocess.CalledProcessError as e:
        output(f"Failed to start http-proxy: {e}", 1)
    finally:
        os.remove(proxy_lock_file)

if settings["useProxy"] and settings["proxyAddress"] == "http://127.0.0.1:8080":
    run_http_proxy()
else:
    output("Proxy disabled in settings.",2)
        
def get_driver():
    global driver
    if driver is None:  # Check if driver needs to be initialized
        manage_session()  # Ensure we can start a session
        driver = setup_driver()
        output("\nCHROME DRIVER INITIALISED: Try not to exit the script before it detaches.",2)
    return driver

def quit_driver():
    global driver
    if driver:
        driver.quit()
        output("\nCHROME DRIVER DETACHED: It is now safe to exit the script.",2)
        driver = None
        release_session()  # Mark the session as closed

def manage_session():
    current_session = session_path
    current_timestamp = int(time.time())
    session_started = False
    new_message = True
    output_priority = 1

    while True:
        try:
            with open(status_file_path, "r+") as file:
                flock(file, LOCK_EX)
                status = json.load(file)

                # Clean up expired sessions
                for session_id, timestamp in list(status.items()):
                    if current_timestamp - timestamp > 300:  # 5 minutes
                        del status[session_id]
                        output(f"Removed expired session: {session_id}", 3)

                # Check for available slots, exclude current session from count
                active_sessions = {k: v for k, v in status.items() if k != current_session}
                if len(active_sessions) < settings['maxSessions']:
                    status[current_session] = current_timestamp
                    file.seek(0)
                    json.dump(status, file)
                    file.truncate()
                    output(f"Session started: {current_session} in {status_file_path}", 3)
                    flock(file, LOCK_UN)
                    session_started = True
                    break
                flock(file, LOCK_UN)

            if not session_started:
                output(f"Waiting for slot. Current sessions: {len(active_sessions)}/{settings['maxSessions']}", output_priority)
                if new_message:
                    new_message = False
                    output_priority = 3
                time.sleep(random.randint(5, 15))
            else:
                break

        except FileNotFoundError:
            # Create file if it doesn't exist
            with open(status_file_path, "w") as file:
                flock(file, LOCK_EX)
                json.dump({}, file)
                flock(file, LOCK_UN)
        except json.decoder.JSONDecodeError:
            # Handle empty or corrupt JSON
            with open(status_file_path, "w") as file:
                flock(file, LOCK_EX)
                output("Corrupted status file. Resetting...", 3)
                json.dump({}, file)
                flock(file, LOCK_UN)

def release_session():
    current_session = session_path
    current_timestamp = int(time.time())

    with open(status_file_path, "r+") as file:
        flock(file, LOCK_EX)
        status = json.load(file)
        if current_session in status:
            del status[current_session]
            file.seek(0)
            json.dump(status, file)
            file.truncate()
        flock(file, LOCK_UN)
        output(f"Session released: {current_session}", 3)

def get_seed_phrase_from_file(screenshots_path):
    seed_file_path = os.path.join(screenshots_path, 'seed.txt')
    if os.path.exists(seed_file_path):
        with open(seed_file_path, 'r') as file:
            return file.read().strip()
    return None

def check_login():
    global screenshot_path, step, session_path
    xpath = "//p[contains(text(), 'Seed phrase')]/ancestor-or-self::*/textarea"
    input_field = move_and_click(xpath, 5, True, "locate seedphrase textbox", step, "clickable")
    
    if input_field:
        seed_phrase = get_seed_phrase_from_file(screenshots_path)
        
        if not seed_phrase and int(step) < 100:
            seed_phrase = validate_seed_phrase()
            output("WARNING: Your seedphrase will be saved as an unencrypted file on your local filesystem if you choose 'y'!",1)
            save_to_file = input("Would you like to save the validated seed phrase to a text file? (y/N): ")
            if save_to_file.lower() == 'y':
                seed_file_path = os.path.join(screenshots_path, 'seed.txt')
                with open(seed_file_path, 'w') as file:
                    file.write(seed_phrase)
                output(f"Seed phrase saved to {seed_file_path}", 3)
        if not seed_phrase and int(step) > 99:
            session = session_path.replace("./selenium/", "")
            output (f"Step {step} - You have become logged out: use './launch.sh tree {session} reset' from the Command Line to configure",1)
            while True:
                input("Restart this PM2 once you have logged in again. Press Enter to continue...")


        input_field.send_keys(seed_phrase)
        output(f"Step {step} - Was successfully able to enter the seed phrase...", 3)
        increase_step()

        # Click the continue button after seed phrase entry:
        xpath = "//button[not(@disabled)]//span[contains(text(), 'Continue')]"
        move_and_click(xpath, 30, True, "click continue after seedphrase entry", step, "clickable")
        increase_step()
    else:
        output("Seed phrase textarea not found within the timeout period.", 2)
 
def next_steps():
    global driver, target_element, settings, backup_path, session_path, step
    driver = get_driver()
    driver.get("https://www.treemine.app/login")
    if step:
        pass
    else:
        step = "01"

    check_login()

    cookies_path = f"{session_path}/cookies.json"
    cookies = driver.get_cookies()
    with open(cookies_path, 'w') as file:
        json.dump(cookies, file)

def find_working_link(old_step):
    global driver, screenshots_path, settings, step
    output(f"Step {step} - Attempting to open a link Following Twitter...",2)

    start_app_xpath = "//p[contains(text(), 'RT')]"

    try:
        start_app_buttons = WebDriverWait(driver, 5).until(EC.presence_of_all_elements_located((By.XPATH, start_app_xpath)))
        clicked = False

        for button in reversed(start_app_buttons):
            actions = ActionChains(driver)
            actions.move_to_element(button).pause(0.2)
            try:
                if settings['debugIsOn']:
                    driver.save_screenshot(f"{screenshots_path}/{step} - Find working link.png".format(screenshots_path))
                actions.perform()
                driver.execute_script("arguments[0].click();", button)
                clicked = True
                break
            except StaleElementReferenceException:
                continue
            except ElementClickInterceptedException:
                continue

        if not clicked:
            output(f"Step {step} - None of the 'Follow on Twitter' buttons were clickable.\n",1)
            if settings['debugIsOn']:
                screenshot_path = f"{screenshots_path}/{step}-no-clickable-button.png"
                driver.save_screenshot(screenshot_path)
            return False
        else:
            output(f"Step {step} - Successfully able to open a link to Follow on Twitter..\n",3)
            if settings['debugIsOn']:
                screenshot_path = f"{screenshots_path}/{step}-app-opened.png"
                driver.save_screenshot(screenshot_path)
            return True

    except TimeoutException:
        output(f"Step {step} - Failed to find the 'Follow on Twitter' button within the expected timeframe.\n",1)
        if settings['debugIsOn']:
            screenshot_path = f"{screenshots_path}/{step}-timeout-finding-button.png"
            driver.save_screenshot(screenshot_path)
        return False
    except Exception as e:
        output(f"Step {step} - An error occurred while trying to Follow on Twitter: {e}\n",1)
        if settings['debugIsOn']:
            screenshot_path = f"{screenshots_path}/{step}-unexpected-error-following-twitter.png"
            driver.save_screenshot(screenshot_path)
        return False

def full_claim():
    global driver, target_element, settings, session_path, step, random_offset
    driver = get_driver()
    
    step = "100"
    
    def get_seed_phrase(screenshots_path):
        seed_file_path = os.path.join(screenshots_path, 'seed.txt')
        if os.path.exists(seed_file_path):
            with open(seed_file_path, 'r') as file:
                seed_phrase = file.read().strip()
            return seed_phrase
        else:
            return None

    def apply_random_offset(unmodifiedTimer):
        global settings, step, random_offset
        if settings['lowestClaimOffset'] <= settings['highestClaimOffset']:
            random_offset = random.randint(settings['lowestClaimOffset'], settings['highestClaimOffset'])
            modifiedTimer = unmodifiedTimer + random_offset
            output(f"Step {step} - Random offset applied to the wait timer of: {random_offset} minutes.", 2)
            return modifiedTimer
    
    driver.get("https://www.treemine.app/missions")
    
    check_login()
    increase_step()

    driver.get("https://www.treemine.app/missions")

    xpath = "//button[contains(text(), 'AXE')]"
    move_and_click(xpath, 30, True, "click the AXE button", step, "clickable")
    increase_step()

    def extract_minutes_from_string(text):
        match = re.search(r'(\d+)', text)
        if match:
            return int(match.group(1))
        return None

    xpath = "//span[contains(., 'minutes after')]"
    axe_time = move_and_click(xpath, 5, False, "check the axe time", step, "visible")
    if axe_time:
        minutes = extract_minutes_from_string(axe_time.text)
        if minutes is not None:
            output(f"Step {step} - The axe can not be claimed for another {minutes} minutes.", 2)
    else:
        find_working_link(step)
    increase_step()

    driver.get("https://www.treemine.app/miner")
    get_balance(False)
    increase_step()

    wait_time_text = get_wait_time(step, "pre-claim") 

    if wait_time_text != pot_full:
        matches = re.findall(r'(\d+)([hm])', wait_time_text)
        remaining_wait_time = (sum(int(value) * (60 if unit == 'h' else 1) for value, unit in matches)) + random_offset
        if remaining_wait_time < 5 or settings["forceClaim"]:
            settings['forceClaim'] = True
            output(f"Step {step} - the remaining time to claim is less than the random offset, so applying: settings['forceClaim'] = True", 3)
        else:
            if remaining_wait_time > 90:
                output(f"Step {step} - Initial wait time returned as {remaining_wait_time}.",3)
                increase_step()
                remaining_wait_time = 90
                random_offset = 0
                wait_time_text = "1h30m"
                output(f"Step {step} - As there are no gas fees with Tree coin - claim forced to 90 minutes.",3)
                increase_step()
            output(f"STATUS: Considering {wait_time_text}, we'll go back to sleep for {remaining_wait_time} minutes.", 1)
            return remaining_wait_time

    if wait_time_text == "Unknown":
      return 15

    try:
        output(f"Step {step} - The pre-claim wait time is : {wait_time_text} and random offset is {random_offset} minutes.",1)
        increase_step()

        if wait_time_text == pot_full or settings['forceClaim']:
            try:
                original_window = driver.current_window_handle
                xpath = "//button[contains(text(), 'Check NEWS')]"
                move_and_click(xpath, 3, True, "check for NEWS.", step, "clickable")
                driver.switch_to.window(original_window)
            except TimeoutException:
                if settings['debugIsOn']:
                    output(f"Step {step} - No news to check or button not found.",3)
            increase_step()

            try:
                # Click on the "Claim HOT" button:
                xpath = "//button[contains(text(), 'Claim')]"
                move_and_click(xpath, 30, True, "click the claim button", step, "clickable")
                increase_step()

                # Now let's try again to get the time remaining until filled. 
                # 4th April 24 - Let's wait for the spinner to disappear before trying to get the new time to fill.
                output(f"Step {step} - Let's wait for the pending Claim spinner to stop spinning...",2)
                time.sleep(5)
                wait = WebDriverWait(driver, 240)
                spinner_xpath = "//*[contains(@class, 'spinner')]" 
                try:
                    wait.until(EC.invisibility_of_element_located((By.XPATH, spinner_xpath)))
                    output(f"Step {step} - Pending action spinner has stopped.\n",3)
                except TimeoutException:
                    output(f"Step {step} - Looks like the site has lag - the Spinner did not disappear in time.\n",2)
                increase_step()
                wait_time_text = get_wait_time(step, "post-claim") 
                matches = re.findall(r'(\d+)([hm])', wait_time_text)
                total_wait_time = apply_random_offset(sum(int(value) * (60 if unit == 'h' else 1) for value, unit in matches))
                increase_step()

                if total_wait_time > 90:
                    total_wait_time = 90
                    output(f"Step {step} - As there are no gas fees with Tree coin - claim forced to 90 minutes.",2)
                    increase_step()

                get_balance(True)

                if wait_time_text == "Filled":
                    output(f"STATUS: The wait timer is still showing: Filled.",1)
                    output(f"Step {step} - This means either the claim failed, or there is >4 minutes lag in the game.",1)
                    output(f"Step {step} - We'll check back in 1 hour to see if the claim processed and if not try again.",2)
                else:
                    output(f"STATUS: Successful Claim: Next claim {wait_time_text} / {total_wait_time} minutes.",1)
                return max(60, total_wait_time)

            except TimeoutException:
                output(f"STATUS: The claim process timed out: Maybe the site has lag? Will retry after one hour.",1)
                return 60
            except Exception as e:
                output(f"STATUS: An error occurred while trying to claim: {e}\nLet's wait an hour and try again",1)
                return 60

        else:
            # If the wallet isn't ready to be claimed, calculate wait time based on the timer provided on the page
            matches = re.findall(r'(\d+)([hm])', wait_time_text)
            if matches:
                total_time = sum(int(value) * (60 if unit == 'h' else 1) for value, unit in matches)
                total_time += 1
                total_time = max(5, total_time) # Wait at least 5 minutes or the time
                output(f"Step {step} - Not Time to claim this wallet yet. Wait for {total_time} minutes until the storage is filled.",2)
                return total_time 
            else:
                output(f"Step {step} - No wait time data found? Let's check again in one hour.",2)
                return 60  # Default wait time when no specific time until filled is found.
    except Exception as e:
        output(f"Step {step} - An unexpected error occurred: {e}",1)
        return 60  # Default wait time in case of an unexpected error
        
def get_balance(claimed=False):
    global step
    prefix = "After" if claimed else "Before"
    default_priority = 2 if claimed else 3

    # Dynamically adjust the log priority
    priority = max(settings['verboseLevel'], default_priority)

    # Construct the specific balance XPath
    balance_text = f'{prefix} BALANCE:' if claimed else f'{prefix} BALANCE:'
    balance_xpath = f"//span[contains(text(), 'TREE Balance:')]/following-sibling::span[1]"

    try:
        # Wait for the element to be visible based on the XPath
        element = WebDriverWait(driver, 10).until(
            EC.visibility_of_element_located((By.XPATH, balance_xpath))
        )

        # Check if element is not None and process the balance
        if element:
            balance_part = element.text.strip()
            output(f"Step {step} - {balance_text} {balance_part}", priority)

    except NoSuchElementException:
        output(f"Step {step} - Element containing '{prefix} Balance:' was not found.", priority)
    except Exception as e:
        output(f"Step {step} - An error occurred: {str(e)}", priority)  # Provide error as string for logging

    # Increment step function, assumed to handle next step logic
    increase_step()


def get_wait_time(step_number="108", beforeAfter = "pre-claim", max_attempts=2):
    
    for attempt in range(1, max_attempts + 1):
        try:
            xpath = f"//div[contains(., 'Storage')]//p[contains(., '{pot_full}') or contains(., '{pot_filling}')]"
            wait_time_element = move_and_click(xpath, 20, True, f"get the {beforeAfter} wait timer", step, "visible")
            # Check if wait_time_element is not None
            if wait_time_element is not None:
                return wait_time_element.text
            else:
                output(f"Step {step} - Attempt {attempt}: Wait time element not found. Clicking the 'Storage' link and retrying...",3)
                storage_xpath = "//h4[text()='Storage']"
                move_and_click(storage_xpath, 30, True, "click the 'storage' link", f"{step} recheck", "clickable")
                output(f"Step {step} - Attempted to select strorage again...",3)
            return wait_time_element.text

        except TimeoutException:
            if attempt < max_attempts:  # Attempt failed, but retries remain
                output(f"Step {step} - Attempt {attempt}: Wait time element not found. Clicking the 'Storage' link and retrying...",3)
                storage_xpath = "//h4[text()='Storage']"
                move_and_click(storage_xpath, 30, True, "click the 'storage' link", f"{step} recheck", "clickable")
            else:  # No retries left after initial failure
                output(f"Step {step} - Attempt {attempt}: Wait time element not found.",3)

        except Exception as e:
            output(f"Step {step} - An error occurred on attempt {attempt}: {e}",3)

    # If all attempts fail         
    return "Unknown"

def clear_screen():
    # Attempt to clear the screen after entering the seed phrase or mobile phone number.
    # For Windows
    if os.name == 'nt':
        os.system('cls')
    # For macOS and Linux
    else:
        os.system('clear')

def restore_from_backup(path):
    global step, session_path
    if os.path.exists(path):
        try:
            quit_driver()
            shutil.rmtree(session_path)
            shutil.copytree(path, session_path, dirs_exist_ok=True)
            driver = get_driver()
            driver.get(url)
            WebDriverWait(driver, 10).until(lambda d: d.execute_script('return document.readyState') == 'complete')
            output(f"Step {step} - Backup restored successfully.",2)
            return True
        except Exception as e:
            output(f"Step {step} - Error restoring backup: {e}\n",1)
            return False
    else:
        output(f"Step {step} - Backup directory does not exist.\n",1)
        return False

def move_and_click(xpath, wait_time, click, action_description, old_step, expectedCondition):
    global driver, screenshots_path, settings, step
    target_element = None
    failed = False

    def timer():
        return random.randint(0, 2) / 10

    output(f"Step {step} - Attempting to {action_description}...", 2)

    try:
        wait = WebDriverWait(driver, wait_time)
        # Check and prepare the element based on the expected condition
        if expectedCondition == "visible":
            target_element = wait.until(EC.visibility_of_element_located((By.XPATH, xpath)))
        elif expectedCondition == "present":
            target_element = wait.until(EC.presence_of_element_located((By.XPATH, xpath)))
        elif expectedCondition == "invisible":
            wait.until(EC.invisibility_of_element_located((By.XPATH, xpath)))
            return None  # Early return as there's no element to interact with
        elif expectedCondition == "clickable":
            target_element = wait.until(EC.element_to_be_clickable((By.XPATH, xpath)))

        # Before interacting, check for and remove overlays if click is needed or visibility is essential
        if click or expectedCondition in ["visible", "clickable"]:
            clear_overlays(target_element, step)

        # Perform actions if the element is found and clicking is requested
        if click and target_element:
            try:
                actions = ActionChains(driver)
                actions.pause(timer()).move_to_element(target_element).pause(timer()).click().perform()
                output(f"Step {step} - Successfully able to {action_description} using ActionChains.", 3)
            except ElementClickInterceptedException:
                output("Step {step} - Element click intercepted, attempting JavaScript click as fallback...", 3)
                driver.execute_script("arguments[0].click();", target_element)
                output(f"Step {step} - Was able to {action_description} using JavaScript fallback.", 3)

    except TimeoutException:
        output(f"Step {step} - Timeout while trying to {action_description}.", 3)
    except Exception as e:
        output(f"Step {step} - An error occurred while trying to {action_description}: {e}", 1)
    finally:
        if settings['debugIsOn']:
            screenshot_path = f"{screenshots_path}/{step}-{action_description}.png"
            driver.save_screenshot(screenshot_path)
        return target_element

def clear_overlays(target_element, old_step):
    # Get the location of the target element
    element_location = target_element.location_once_scrolled_into_view
    overlays = driver.find_elements(By.XPATH, "//*[contains(@style,'position: absolute') or contains(@style,'position: fixed')]")
    for overlay in overlays:
        overlay_rect = overlay.rect
        # Check if overlay covers the target element
        if (overlay_rect['x'] <= element_location['x'] <= overlay_rect['x'] + overlay_rect['width'] and
            overlay_rect['y'] <= element_location['y'] <= overlay_rect['y'] + overlay_rect['height']):
            driver.execute_script("arguments[0].style.display = 'none';", overlay)
            output(f"Step {step} - Removed an overlay covering the target.", 3)

def validate_seed_phrase():
    # Let's take the user inputed seed phrase and carry out basic validation
    while True:
        # Prompt the user for their seed phrase
        if settings['hideSensitiveInput']:
            seed_phrase = getpass.getpass(f"Step {step} - Please enter your 12-word seed phrase (your input is hidden): ")
        else:
            seed_phrase = input(f"Step {step} - Please enter your 12-word seed phrase (your input is visible): ")
        try:
            if not seed_phrase:
              raise ValueError(f"Step {step} - Seed phrase cannot be empty.")

            words = seed_phrase.split()
            if len(words) != 12:
                raise ValueError(f"Step {step} - Seed phrase must contain exactly 12 words.")

            pattern = r"^[a-z ]+$"
            if not all(re.match(pattern, word) for word in words):
                raise ValueError(f"Step {step} - Seed phrase can only contain lowercase letters and spaces.")
            return seed_phrase  # Return if valid

        except ValueError as e:
            output(f"Error: {e}",1)

# Start a new PM2 process
def start_pm2_app(script_path, app_name, session_name):
    interpreter_path = "venv/bin/python3"
    command = f"NODE_NO_WARNINGS=1 pm2 start {script_path} --name {app_name} --interpreter {interpreter_path} --watch {script_path} -- {session_name}"
    subprocess.run(command, shell=True, check=True)

# Save the new PM2 process
def save_pm2():
    command = f"NODE_NO_WARNINGS=1 pm2 save"
    result = subprocess.run(command, shell=True, text=True, capture_output=True)
    print(result.stdout)

def backup_telegram():
    global session_path, step

    # Ask the user if they want to backup their Telegram directory
    backup_prompt = input("Would you like to backup your Telegram directory? (Y/n): ").strip().lower()
    if backup_prompt == 'n':
        output(f"Step {step} - Backup skipped by user choice.", 3)
        return

    # Ask the user for a custom filename
    custom_filename = input("Enter a custom filename for the backup (leave blank for default): ").strip()

    # Define the backup destination path
    if custom_filename:
        backup_directory = os.path.join(os.path.dirname(session_path), f"Telegram:{custom_filename}")
    else:
        backup_directory = os.path.join(os.path.dirname(session_path), "Telegram")

    try:
        # Ensure the backup directory exists and copy the contents
        if not os.path.exists(backup_directory):
            os.makedirs(backup_directory)
        shutil.copytree(session_path, backup_directory, dirs_exist_ok=True)
        output(f"Step {step} - We backed up the session data in case of a later crash!", 3)
    except Exception as e:
        output(f"Step {step} - Oops, we weren't able to make a backup of the session data! Error: {e}", 1)

def main():
    global session_path, settings, step
    if not settings["forceNewSession"]:
        load_settings()
    cookies_path = os.path.join(session_path, 'cookies.json')
    if os.path.exists(cookies_path) and not settings['forceNewSession']:
        output("Resuming the previous session...",2)
    else:
        next_steps()
        quit_driver()

        try:
            shutil.copytree(session_path, backup_path, dirs_exist_ok=True)
            output("We backed up the session data in case of a later crash!",3)
        except Exception as e:
            output("Oops, we weren't able to make a backup of the session data! Error:", 1)

        pm2_session = session_path.replace("./selenium/", "")
        output(f"You could add the new/updated session to PM use: pm2 start {script} --interpreter venv/bin/python3 --name {pm2_session} -- {pm2_session}",1)
        user_choice = input("Enter 'y' to continue to 'claim' function, 'e' to exit, 'a' or <enter> to automatically add to PM2: ").lower()

        if user_choice == "e":
            output("Exiting script. You can resume the process later.", 1)
            sys.exit()
        elif user_choice == "a" or not user_choice:
            start_pm2_app(script, pm2_session, pm2_session)
            user_choice = input("Should we save your PM2 processes? (Y/n): ").lower()
            if user_choice == "y" or not user_choice:
                save_pm2()
            output(f"You can now watch the session log into PM2 with: pm2 logs {pm2_session}", 2)
            sys.exit()

    while True:
        manage_session()
        wait_time = full_claim()
        if wait_time > 90:
            output (f"**Notice**: High wait time returned of {wait_time}. Limiting it to 90 minutes.", 2)
            wait_time = 90

        if os.path.exists(status_file_path):
            with open(status_file_path, "r+") as file:
                status = json.load(file)
                if session_path in status:
                    del status[session_path]
                    file.seek(0)
                    json.dump(status, file)
                    file.truncate()
                    output(f"Session released: {session_path}",3)

        quit_driver()
                
        now = datetime.now()
        next_claim_time = now + timedelta(minutes=wait_time)
        this_claim_str = now.strftime("%d %B - %H:%M")
        next_claim_time_str = next_claim_time.strftime("%d %B - %H:%M")
        output(f"{this_claim_str} | Need to wait until {next_claim_time_str} before the next claim attempt. Approximately {wait_time} minutes.", 1)
        if settings["forceClaim"]:
            settings["forceClaim"] = False

        while wait_time > 0:
            this_wait = min(wait_time, 15)
            now = datetime.now()
            timestamp = now.strftime("%H:%M")
            output(f"[{timestamp}] Waiting for {this_wait} more minutes...",3)
            time.sleep(this_wait * 60)  # Convert minutes to seconds
            wait_time -= this_wait
            if wait_time > 0:
                output(f"Updated wait time: {wait_time} minutes left.",3)


if __name__ == "__main__":
    main()
