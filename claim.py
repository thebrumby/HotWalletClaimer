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

# Initiate global variables:
driver = None
target_element = None

# Global variables
settings = {
    "forceClaim": False,
    "debugIsOn": False,
    "hideSensitiveInput": True,
    "screenshotQRCode": True,
    "maxSessions": 1,
    "verboseLevel": 2,
    "forceNewSession": False,
}

print("Initialising the HOT Wallet Auto-claim Python Script - Good Luck!")

settings_file = "variables.txt"
status_file_path = "status.txt"

def output(string, level):
    if settings['verboseLevel'] >= level:
        print(string)

def load_settings():
    global settings
    if os.path.exists(settings_file):
        with open(settings_file, "r") as f:
            settings = json.load(f)
        output("Settings loaded successfully.",3)
    else:
        save_settings()  # Create the file with default settings

def save_settings():
    global settings
    with open(settings_file, "w") as f:
        json.dump(settings, f, indent=4)
    output("\nSettings saved successfully.",3)

def update_settings():
    global settings
    load_settings()  # Assuming this function is defined to load settings from a file or similar source

    output("\nCurrent settings:",1)
    for key, value in settings.items():
        output(f"{key}: {value}",1)

    # Function to simplify the process of updating settings
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
        output("Invalid input. Number of sessions remains unchanged.",1)

    try:
        new_verbose_level = int(input(f"\nEnter the number for how much information you want displaying in the console.\n 3 = all messages, 2 = claim steps, 1 = minimal steps\n(current: {settings['verboseLevel']}): "))
        if 1 <= new_verbose_level <= 3:
            settings["verboseLevel"] = new_verbose_level
            output("Verbose level updated successfully.",2)
        else:
            output("Invalid input. Please enter a number between 1 and 3. Verbose level remains unchanged.",2)
    except ValueError:
        output("Invalid input. Verbose level remains unchanged.",2)

    save_settings()

    update_setting("forceNewSession", "Overwrite existing session and Force New Login? Use this if your saved session has crashed\nOne-Time only (setting not saved): ", settings["forceNewSession"])

    output("\nRevised settings:",1)
    for key, value in settings.items():
        output(f"{key}: {value}",1)
    output("",1)

# Set up paths and sessions:
user_input = ""
session_path = "./selenium/{}".format(user_input)
os.makedirs(session_path, exist_ok=True)
screenshots_path = "./screenshots/{}".format(user_input)
os.makedirs(screenshots_path, exist_ok=True)
output(f"Our screenshot path is {screenshots_path}",3)
backup_path = "./backups/{}".format(user_input)
os.makedirs(backup_path, exist_ok=True)
output(f"Our screenshot path is {backup_path}",3)

def get_session_id():
    global settings
    """Prompts the user for a session ID or determines the next sequential ID.

    Returns:
        str: The entered session ID or the generated sequential ID.
    """

    user_input = input("Enter your unique Session Name here, or hit <enter> for the next sequential folder: ")
    user_input = user_input.strip()

    # Check for existing session folders
    screenshots_dir = "./screenshots/"
    dir_contents = os.listdir(screenshots_dir)
    numeric_dirs = [dir_name for dir_name in dir_contents if dir_name.isdigit() and os.path.isdir(os.path.join(screenshots_dir, dir_name))]
    next_session_id = "1"
    if numeric_dirs:
        highest_numeric_dir = max(map(int, numeric_dirs))
        next_session_id = str(highest_numeric_dir + 1)

    # Use the next sequential ID if no user input was provided
    if not user_input:
        user_input = next_session_id
    return user_input

# Update the settings based on user input
if len(sys.argv) > 1:
        user_input = sys.argv[1]  # Get session ID from command-line argument
        output(f"Session ID provided: {user_input}",2)
        # Safely check for a second argument
        if len(sys.argv) > 2 and sys.argv[2] == "debug":
            settings['debugIsOn'] = True
else:
    user_input = input("Should we update our settings? (Default:<enter> / Yes = y): ").strip().lower()
    if user_input == "y":
        update_settings()
    user_input = get_session_id()


session_path = "./selenium/{}".format(user_input)
os.makedirs(session_path, exist_ok=True)
screenshots_path = "./screenshots/{}".format(user_input)
os.makedirs(screenshots_path, exist_ok=True)
backup_path = "./backups/{}".format(user_input)
os.makedirs(backup_path, exist_ok=True)

# Define our base path for debugging screenshots
screenshot_base = os.path.join(screenshots_path, "screenshot")

def setup_driver(chromedriver_path):

    service = Service(chromedriver_path)
    chrome_options = webdriver.ChromeOptions()
    chrome_options.add_argument("user-data-dir={}".format(session_path))
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--log-level=3")  # Set log level to suppress INFO and WARNING messages
    chrome_options.add_argument("--disable-bluetooth")
    chrome_options.add_argument("--mute-audio")
    # chrome_options.add_argument("--incognito")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_experimental_option('excludeSwitches', ['enable-logging'])
    chrome_options.add_experimental_option("detach", True)

    # Compatibility Handling and error testing:
    try:
        driver = webdriver.Chrome(service=service, options=chrome_options)
        return driver
    except Exception as e:
        output(f"Initial ChromeDriver setup may have failed: {e}",1)
        output("Please ensure you have the correct ChromeDriver version for your system.",1)
        output("If you copied the GitHub commands, ensure all lines executed.",1)
        output("Visit https://chromedriver.chromium.org/downloads to find the right version.",1)
        exit(1)

# Enter the correct the path to your ChromeDriver here
chromedriver_path = "/usr/local/bin/chromedriver"

def get_driver():
    global driver
    if driver is None:  # Check if driver needs to be initialized
        driver = setup_driver(chromedriver_path)
        load_cookies()
    return driver

def load_cookies():
    global driver
    cookies_path = f"{session_path}/cookies.json"
    if os.path.exists(cookies_path):
        with open(cookies_path, 'r') as file:
            cookies = json.load(file)
            for cookie in cookies:
                driver.add_cookie(cookie)

def quit_driver():
    global driver
    if driver:
        driver.quit()
        driver = None
        
def manage_session():
    current_session = session_path
    current_timestamp = int(time.time())

    while True:
        try:
            with open(status_file_path, "r+") as file:
                status = json.load(file)

                # Clean up expired sessions
                for session_id, timestamp in list(status.items()):  # Important to iterate over a copy
                    if current_timestamp - timestamp > 300:  # 5 minutes
                        del status[session_id]
                        output(f"Removed expired session: {session_id}",3)

                # Check for available slots
                if len(status) < settings['maxSessions']:
                    status[current_session] = current_timestamp
                    file.seek(0)  # Rewind to beginning
                    json.dump(status, file)
                    file.truncate()  # Ensure clean overwrite
                    output(f"Session started: {current_session} in {status_file_path}",3)
                    break  # Exit the loop once session is acquired

            output(f"Waiting for slot. Current sessions: {len(status)}/{settings['maxSessions']}",3)
            time.sleep(random.randint(20, 40))

        except FileNotFoundError:
            # Create file if it doesn't exist
            with open(status_file_path, "w") as file:
                json.dump({}, file)
        except json.decoder.JSONDecodeError:
            # Handle empty or corrupt JSON 
            output("Corrupted status file. Resetting...",3)
            with open(status_file_path, "w") as file:
                json.dump({}, file)
 
def log_into_telegram():
    global driver, target_element, session_path, screenshots_path, backup_path, settings

    def visible_QR_code():
        global driver, screenshots_path
        try:
            # Load the page
            driver.get("https://web.telegram.org/k/#@herewalletbot")
            # Wait for the page to be fully loaded
            WebDriverWait(driver, 10).until(lambda d: d.execute_script('return document.readyState') == 'complete')
            
            # Define the XPath and interact with the QR code
            xpath = "//canvas[@class='qr-canvas']"
            QR_code = move_and_click(xpath, 5, False, "obtain QR code", "00", "visible")
            # Take a screenshot of the QR code
            QR_code.screenshot('{}/00 - Generate QR code.png'.format(screenshots_path))
            
            # Load the image and decode the QR
            image = Image.open('{}/00 - Generate QR code.png'.format(screenshots_path))
            decoded_objects = decode(image)
            
            # Print decoded data to console
            if decoded_objects:
                # Display the first decoded QR code data in the console as ASCII art
                data = decoded_objects[0].data.decode()
                qrcode_terminal.draw(data)
            
            # Test to see if QR code disappears
            wait = WebDriverWait(driver, 25)
            wait.until(EC.invisibility_of_element_located((By.XPATH, xpath)))
            output ("Step 00 - Successfully scanned QR code.", 2)
            return True
        
        except TimeoutException:
            return False

    if os.path.exists(session_path):
        shutil.rmtree(session_path)
    os.makedirs(session_path, exist_ok=True)
    if os.path.exists(screenshots_path):
        shutil.rmtree(screenshots_path)
    os.makedirs(screenshots_path, exist_ok=True)
    if os.path.exists(backup_path):
        shutil.rmtree(backup_path)
    os.makedirs(backup_path, exist_ok=True)

    driver = get_driver()

    output(f"Our screenshot path is {screenshots_path}\n",1)
    output("*** Important: Having @HereWalletBot open in your Telegram App might stop this script loggin in! ***\n",2)
    
    # QR Code Method
    if settings['screenshotQRCode']:
        try:

            while True:
                if visible_QR_code():  # QR code not found
                    test_for_2fa()
                    return  # Exit the function entirely

                # If we reach here, it means the QR code is still present:
                choice = input("\nStep 00a - QR Code still present. Retry (r) with a new QR code or switch to the OTP method (enter): ")
                print("")
                if choice.lower() == 'r':
                    visible_QR_code()
                else:
                    break

        except TimeoutException:
            output("Canvas not found: Restart the script and retry the QR Code or switch to the OTP method.", 1)

    # OTP Login Method
    output("Initiating the One-Time Password (OTP) method...\n",1)
    driver.get("https://web.telegram.org/k/#@herewalletbot")
    xpath = "//button[contains(@class, 'btn-primary') and contains(., 'Log in by phone Number')]"
    move_and_click(xpath, 30, True, "switch to log in by phone number", "01a", "clickable")

    # Country Code Selection
    xpath = "//div[@class='input-field-input']//span[@class='i18n']"    
    target_element = move_and_click(xpath, 30, True, "update users country", "01b", "clickable")
    user_input = input("Please enter your Country Name as it appears in the Telegram list: ").strip()  
    target_element.send_keys(user_input)
    target_element.send_keys(Keys.RETURN) 

    # Phone Number Input
    xpath = "//div[@class='input-field-input' and @inputmode='decimal']"
    target_element = move_and_click(xpath, 30, True, "request users phone number", "01c", "clickable")
    def validate_phone_number(phone):
        # Regex for validating an international phone number without leading 0 and typically 7 to 15 digits long
        pattern = re.compile(r"^[1-9][0-9]{6,14}$")
        return pattern.match(phone)

    while True:
        if settings['hideSensitiveInput']:
            user_phone = getpass.getpass("Please enter your phone number without leading 0 (hidden input): ")
        else:
            user_phone = input("Please enter your phone number without leading 0 (visible input): ")
    
        if validate_phone_number(user_phone):
            output("Step 01c - Valid phone number entered.",3)
            break
        else:
            output("Step 01c - Invalid phone number, must be 7 to 15 digits long and without leading 0.",1)
    target_element.send_keys(user_phone)

    # Wait for the "Next" button to be clickable and click it    
    xpath = "//button[contains(@class, 'btn-primary') and .//span[contains(text(), 'Next')]]"
    move_and_click(xpath, 5, True, "click next to proceed to OTP entry", "01d", "visible")

    try:
        # Attempt to locate and interact with the OTP field
        wait = WebDriverWait(driver, 20)
        password = wait.until(EC.element_to_be_clickable((By.XPATH, "//input[@type='tel']")))
        if settings['debugIsOn']:
            time.sleep(3)
            driver.save_screenshot("{}/01e_Ready_for_OTP.png".format(screenshots_path))
        otp = input("Step 01e - What is the Telegram OTP from your app? ")
        password.click()
        password.send_keys(otp)
        output("Step 01e - Let's try to log in using your Telegram OTP.\n",3)

    except TimeoutException:
        # OTP field not found 
        output("Step 01e - OTP entry has failed - maybe you entered the wrong code, or possible flood cooldown issue.",1)

    except Exception as e:  # Catch any other unexpected errors
        output("Login failed. Error: {e}", 1) 
        if settings['debugIsOn']:
            driver.save_screenshot("{}/01-error_Something_Occured.png".format(screenshots_path))
    
    test_for_2fa()

    if settings['debugIsOn']:
        time.sleep(3)
        driver.save_screenshot("{}/01f_After_Entering_OTP.png".format(screenshots_path))

def test_for_2fa():
    global settings, driver, screenshots_path
    try:
        WebDriverWait(driver, 30).until(lambda d: d.execute_script('return document.readyState') == 'complete')
        xpath = "//input[@type='password' and contains(@class, 'input-field-input')]"
        fa_input = move_and_click(xpath, 5, False, "check for 2FA requirement (for most users this will timeout)", "01g", "present")
        if fa_input:
            if settings['hideSensitiveInput']:
                tg_password = getpass.getpass("Step 01g - Enter your Telegram 2FA password: ")
            else:
                tg_password = input("Step 01g - Enter your Telegram 2FA password: ")
            fa_input.send_keys(tg_password + Keys.RETURN)
            output("Step 01g - 2FA password sent.\n", 3)
            output("Step 01h - Checking if the 2FA password is marked as incorrect.\n", 2)
            xpath = "//*[contains(text(), 'Incorrect password')]"
            try:
                incorrect_password = WebDriverWait(driver, 5).until(EC.visibility_of_element_located((By.XPATH, xpath)))
                output("Step 01h - 2FA password is marked as incorrect by Telegram - check your debug screenshot if active.", 1)
                if settings['debugIsOn']:
                    screenshot_path = f"{screenshots_path}/01h-Test QR code after session is resumed.png"
                    driver.save_screenshot(screenshot_path)
                sys.exit()  # Exit if incorrect password is detected
            except TimeoutException:
                pass

            output("Step 01h - No password error found.", 3)
            xpath = "//input[@type='password' and contains(@class, 'input-field-input')]"
            fa_input = move_and_click(xpath, 5, False, "final check to make sure we are correctly logged in", "01i", "present")
            if fa_input:
                output("Step 01i - 2FA password entry is still showing, check your debug screenshots for further information.\n", 1)
                sys.exit()
            output("Step 01i - 2FA password check appears to have passed OK.\n", 3)
        else:
            output("Step 01g - 2FA input field not found.\n", 1)

    except TimeoutException:
        # 2FA field not found
        output("Step 01g - Two-factor Authorization not required.\n", 3)

    except Exception as e:  # Catch any other unexpected errors
        output(f"Login failed. 2FA Error - you'll probably need to restart the script: {e}", 1)
        if settings['debugIsOn']:
            screenshot_path = f"{screenshots_path}/Step 01g - error: Something Bad Occured.png"
            driver.save_screenshot(screenshot_path)

def next_steps():
    global driver, target_element, settings, backup_path, session_path
    driver = get_driver()

    try:
        driver.get("https://tgapp.herewallet.app/auth/import")
        WebDriverWait(driver, 30).until(lambda d: d.execute_script('return document.readyState') == 'complete')
        
        # Then look for the seed phase textarea:
        xpath = "//p[contains(text(), 'Seed or private key')]/ancestor-or-self::*/textarea"
        input_field = move_and_click(xpath, 30, True, "locate seedphrase textbox", "09", "clickable")
        input_field.send_keys(validate_seed_phrase()) 
        output("Step 09 - Was successfully able to enter the seed phrase...",3)

        # Click the continue button after seed phrase entry:
        xpath = "//button[contains(text(), 'Continue')]"
        move_and_click(xpath, 30, True, "click continue after seedphrase entry", "10", "clickable")

        # Click the account selection button:
        xpath = "//button[contains(text(), 'Select account')]"
        move_and_click(xpath, 120, True, "click continue at account selection screen", "11", "clickable")

        # Click on the Storage link:
        xpath = "//h4[text()='Storage']"
        move_and_click(xpath, 30, True, "click the 'storage' link", "12", "clickable")
        cookies_path = f"{session_path}/cookies.json"
        cookies = driver.get_cookies()
        with open(cookies_path, 'w') as file:
            json.dump(cookies, file)

    except TimeoutException:
        output("Failed to find or switch to the iframe within the timeout period.",1)

    except Exception as e:
        output(f"An error occurred: {e}",1)

def full_claim():
    global driver, target_element, settings, session_path

    driver = get_driver()
    output("\nCHROME DRIVER INITIALISED: If the script exits before detaching, the session may need to be restored.",1)

    try:
        driver.get("https://web.telegram.org/k/#@herewalletbot")
        WebDriverWait(driver, 30).until(lambda d: d.execute_script('return document.readyState') == 'complete')
        output("Step 100 - Attempting to verify if we are logged in (hopefully QR code is not present).",3)
        xpath = "//canvas[@class='qr-canvas']"
        wait = WebDriverWait(driver, 5)
        wait.until(EC.visibility_of_element_located((By.XPATH, xpath)))
        if settings['debugIsOn']:
            screenshot_path = f"{screenshots_path}/100-Test QR code after session is resumed.png"
            driver.save_screenshot(screenshot_path)
        output("Chrome driver reports the QR code is visible: It appears we are no longer logged in.",1)
        output("Most likely you will get a warning that the central input box is not found.",2)
        output("System will try to restore session, or restart the script from CLI force a fresh log in.\n",1)

    except TimeoutException:
        output("Step 100 - nothing found to action. The QR code test passed.\n",3)


    driver.get("https://web.telegram.org/k/#@herewalletbot")
    WebDriverWait(driver, 30).until(lambda d: d.execute_script('return document.readyState') == 'complete')

    if settings['debugIsOn']:
        time.sleep(3)
        driver.save_screenshot("{}/Step 100 Pre-Claim screenshot.png".format(screenshots_path))

    # There is a very unlikely scenario that the chat might have been cleared.
    # In this case, the "START" button needs pressing to expose the chat window!
    xpath = "//button[contains(., 'START')]"
    move_and_click(xpath, 5, True, "check for the start button (should not be present)", "101", "clickable")

    # Let's try to send the start command:
    send_start("102")

    # Now let's try to find a working link to open the launch button
    find_working_link("104")

    # Now let's move to and JS click the "Launch" Button
    xpath = "//button[contains(@class, 'popup-button') and contains(., 'Launch')]"
    move_and_click(xpath, 30, True, "click the 'Launch' button", "105", "clickable")

    # HereWalletBot Pop-up Handling
    select_iframe("106")

    # Click on the Storage link:
    xpath = "//h4[text()='Storage']"
    move_and_click(xpath, 30, True, "click the 'storage' link", "107", "clickable")

    try:
        element = WebDriverWait(driver, 10).until(
            EC.visibility_of_element_located(
                (By.XPATH, "//p[contains(text(), 'HOT Balance:')]/following-sibling::p[1]")
            )
        )
    
        # Retrieve the entire block of text within the parent div of the found <p> element
        if element is not None:
            parent_div = element.find_element(By.XPATH, "./..")
            text_content = parent_div.text 
            balance_part = text_content.split("HOT Balance:\n")[1].strip() if "HOT Balance:\n" in text_content else "No balance info"
            output(f"Step 107 - HOT balance prior to claim: {balance_part}", 2)

    except NoSuchElementException:
        output("107 - Element containing 'HOT Balance:' was not found.", 3)
    except Exception as e:
        print("107 - An error occurred:", e)

    wait_time_text = get_wait_time("108", "pre-claim") 
    if wait_time_text == "Unknown":
      return 5

    try:
        output("Step 108 - The pre-claim wait time is : {}".format(wait_time_text),1)
        if wait_time_text == "Filled" or settings['forceClaim']:
            try:
                original_window = driver.current_window_handle
                xpath = "//button[contains(text(), 'Check NEWS')]"
                move_and_click(xpath, 10, True, "check for NEWS.", "109", "clickable")
                driver.switch_to.window(original_window)
            except TimeoutException:
                if settings['debugIsOn']:
                    output("No news to check or button not found.",3)

            try:
                # Let's double check if we have to reselect the iFrame after news
                # HereWalletBot Pop-up Handling
                select_iframe("109")
                
                # Click on the "Claim HOT" button:
                xpath = "//button[contains(text(), 'Claim HOT')]"
                move_and_click(xpath, 30, True, "click the claim button", "110", "clickable")

                # Now let's try again to get the time remaining until filled. 
                # 4th April 24 - Let's wait for the spinner to disappear before trying to get the new time to fill.
                output("Step 111 - Let's wait for the pending Claim spinner to stop spinning...",2)
                time.sleep(5)
                wait = WebDriverWait(driver, 240)
                spinner_xpath = "//*[contains(@class, 'spinner')]" 
                try:
                    wait.until(EC.invisibility_of_element_located((By.XPATH, spinner_xpath)))
                    output("Step 111 - Pending action spinner has stopped.\n",3)
                except TimeoutException:
                    output("Step 111 - Looks like the site has lag- the Spinner did not disappear in time.\n",2)
                wait_time_text = get_wait_time("112", "post-claim") 
                matches = re.findall(r'(\d+)([hm])', wait_time_text)
                total_wait_time = sum(int(value) * (60 if unit == 'h' else 1) for value, unit in matches)
                total_wait_time += 1
                if wait_time_text == "Filled":
                    output("The wait timer is still showing: Filled.",1)
                    output("This means either the claim failed, or there is >4 minutes lag in the game.",1)
                    output("We'll check back in 1 hour to see if the claim processed and if not try again.",2)
                else:
                    output("Post claim raw wait time: %s & proposed new wait timer = %s minutes." % (wait_time_text, total_wait_time),1)
                return max(60, total_wait_time)

            except TimeoutException:
                output("The claim process timed out: Maybe the site has lag? Will retry after one hour.",2)
                return 60
            except Exception as e:
                output(f"An error occurred while trying to claim: {e}\nLet's wait an hour and try again",1)
                return 60

        else:
            # If the wallet isn't ready to be claimed, calculate wait time based on the timer provided on the page
            matches = re.findall(r'(\d+)([hm])', wait_time_text)
            if matches:
                total_time = sum(int(value) * (60 if unit == 'h' else 1) for value, unit in matches)
                total_time += 1
                total_time = max(5, total_time) # Wait at least 5 minutes or the time
                output("Not Time to claim this wallet yet. Wait for {} minutes until the storage is filled.".format(total_time),2)
                return total_time 
            else:
                output("No wait time data found? Let's check again in one hour.",2)
                return 60  # Default wait time when no specific time until filled is found.
    except Exception as e:
        output("An unexpected error occurred: {}".format(e),1)
        return 60  # Default wait time in case of an unexpected error
        
def get_wait_time(step_number="108", beforeAfter = "pre-claim", max_attempts=2):
    
    for attempt in range(1, max_attempts + 1):
        try:
            xpath = "//div[contains(., 'Storage')]//p[contains(., 'Filled') or contains(., 'to fill')]"
            wait_time_element = move_and_click(xpath, 20, True, f"get the {beforeAfter} wait timer", step_number, "visible")
            # Check if wait_time_element is not None
            if wait_time_element is not None:
                return wait_time_element.text
            else:
                output(f"Step {step_number} - Attempt {attempt}: Wait time element not found. Clicking the 'Storage' link and retrying...",3)
                storage_xpath = "//h4[text()='Storage']"
                move_and_click(storage_xpath, 30, True, "click the 'storage' link", "108 recheck", "clickable")
                output(f"Step {step_number} - Attempted to select strorage again...",3)
            return wait_time_element.text

        except TimeoutException:
            if attempt < max_attempts:  # Attempt failed, but retries remain
                output(f"Attempt {attempt}: Wait time element not found. Clicking the 'Storage' link and retrying...",3)
                storage_xpath = "//h4[text()='Storage']"
                move_and_click(storage_xpath, 30, True, "click the 'storage' link", "107", "clickable")
            else:  # No retries left after initial failure
                output(f"Attempt {attempt}: Wait time element not found.",3)

        except Exception as e:
            output(f"An error occurred on attempt {attempt}: {e}",3)

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

def select_iframe(step):
    global driver, screenshots_path, settings
    output(f"Step {step} - Attempting to switch to the app's iFrame...",2)

    try:
        wait = WebDriverWait(driver, 20)
        popup_body = wait.until(EC.presence_of_element_located((By.CLASS_NAME, "popup-body")))
        iframe = popup_body.find_element(By.TAG_NAME, "iframe")
        driver.switch_to.frame(iframe)
        output(f"Step {step} - Was successfully able to switch to the app's iFrame.\n",3)

        if settings['debugIsOn']:
            screenshot_path = f"{screenshots_path}/{step}-iframe-switched.png"
            driver.save_screenshot(screenshot_path)

    except TimeoutException:
        output(f"Step {step} - Failed to find or switch to the iframe within the timeout period.\n",3)
        if settings['debugIsOn']:
            screenshot_path = f"{screenshots_path}/{step}-iframe-timeout.png"
            driver.save_screenshot(screenshot_path)
    except Exception as e:
        output(f"Step {step} - An error occurred while attempting to switch to the iframe: {e}\n",3)
        if settings['debugIsOn']:
            screenshot_path = f"{screenshots_path}/{step}-iframe-error.png"
            driver.save_screenshot(screenshot_path)

def find_working_link(step):
    global driver, screenshots_path, settings
    output(f"Step {step} - Attempting to open a link for the app...",2)

    start_app_xpath = "//a[@href='https://t.me/herewalletbot/app']"
    try:
        start_app_buttons = WebDriverWait(driver, 30).until(EC.presence_of_all_elements_located((By.XPATH, start_app_xpath)))
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
            output(f"Step {step} - None of the 'Open Wallet' buttons were clickable.\n",1)
            if settings['debugIsOn']:
                screenshot_path = f"{screenshots_path}/{step}-no-clickable-button.png"
                driver.save_screenshot(screenshot_path)
        else:
            output(f"Step {step} - Successfully able to open a link for the app..\n",3)
            if settings['debugIsOn']:
                screenshot_path = f"{screenshots_path}/{step}-app-opened.png"
                driver.save_screenshot(screenshot_path)

    except TimeoutException:
        output(f"Step {step} - Failed to find the 'Open Wallet' button within the expected timeframe.\n",1)
        if settings['debugIsOn']:
            screenshot_path = f"{screenshots_path}/{step}-timeout-finding-button.png"
            driver.save_screenshot(screenshot_path)
    except Exception as e:
        output(f"Step {step} - An error occurred while trying to open the app: {e}\n",1)
        if settings['debugIsOn']:
            screenshot_path = f"{screenshots_path}/{step}-unexpected-error-opening-app.png"
            driver.save_screenshot(screenshot_path)


def send_start(step):
    global driver, screenshots_path, backup_path, settings
    xpath = "//div[contains(@class, 'input-message-container')]/div[contains(@class, 'input-message-input')][1]"
    
    def attempt_send_start():
        nonlocal step  # Allows us to modify the outer function's step variable
        chat_input = move_and_click(xpath, 30, False, "find the chat window/message input box", step, "present")
        if chat_input:
            step_int = int(step) + 1
            new_step = f"{step_int:02}"
            output(f"Step {new_step} - Attempting to send the '/start' command...",2)
            chat_input.send_keys("/start")
            chat_input.send_keys(Keys.RETURN)
            output(f"Step {new_step} - Successfully sent the '/start' command.\n",3)
            if settings['debugIsOn']:
                screenshot_path = f"{screenshots_path}/{new_step}-sent-start.png"
                driver.save_screenshot(screenshot_path)
            return True
        else:
            output(f"Step {step} - Failed to find the message input box.\n",1)
            return False

    if not attempt_send_start():
        # Attempt failed, try restoring from backup and retry
        output(f"Step {step} - Attempting to restore from backup and retry.\n",2)
        if restore_from_backup():
            if not attempt_send_start():  # Retry after restoring backup
                output(f"Step {step} - Retried after restoring backup, but still failed to send the '/start' command.\n",1)
        else:
            output(f"Step {step} - Backup restoration failed or backup directory does not exist.\n",1)

def restore_from_backup():
    if os.path.exists(backup_path):
        try:
            quit_driver()
            shutil.rmtree(session_path)
            shutil.copytree(backup_path, session_path, dirs_exist_ok=True)
            driver = get_driver()
            driver.get("https://web.telegram.org/k/#@herewalletbot")
            WebDriverWait(driver, 30).until(lambda d: d.execute_script('return document.readyState') == 'complete')
            output("Backup restored successfully.\n",2)
            return True
        except Exception as e:
            output(f"Error restoring backup: {e}\n",1)
            return False
    else:
        output("Backup directory does not exist.\n",1)
        return False

def move_and_click(xpath, wait_time, click, action_description, step, expectedCondition):
    global driver, screenshots_path, settings
    target_element = None
    failed = False

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
                actions.move_to_element(target_element).pause(0.2).click().perform()
                output(f"Step {step} - Was able to {action_description} using ActionChains.", 3)
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

def clear_overlays(target_element, step):
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
    # Let's take the user inputed seed phrase and carry o,,ut basic validation
    while True:
        # Prompt the user for their seed phrase
        if settings['hideSensitiveInput']:
            seed_phrase = getpass.getpass("Please enter your 12-word seed phrase (your input is hidden): ")
        else:
            seed_phrase = input("Please enter your 12-word seed phrase (your input is visible): ")
        try:
            if not seed_phrase:
              raise ValueError("Seed phrase cannot be empty.")

            words = seed_phrase.split()
            if len(words) != 12:
                raise ValueError("Seed phrase mus,,,,t contain exactly 12 words.")

            pattern = r"^[a-z ]+$"
            if not all(re.match(pattern, word) for word in words):
                raise ValueError("Seed phrase can only contain lowercase letters and spaces.")
            return seed_phrase  # Return if valid

        except ValueError as e:
            output(f"Error: {e}",1)

# Start a new PM2 process
def start_pm2_app(script_path, app_name, session_name):
    command = f"pm2 start {script_path} --name {app_name} -- {session_name}"
    subprocess.run(command, shell=True, check=True)

# List all PM2 processes
def save_pm2():
    command = "pm2 save"
    result = subprocess.run(command, shell=True, text=True, capture_output=True)
    print(result.stdout)

def main():
    global session_path, settings
    driver = get_driver()
    quit_driver()
    clear_screen()
    if not settings["forceNewSession"]:
        load_settings()
    cookies_path = os.path.join(session_path, 'cookies.json')
    if os.path.exists(cookies_path) and not settings['forceNewSession']:
        output("Resuming the previous session...",2)
    else:
        output("Starting the Telegram & HereWalletBot login process...",2)
        log_into_telegram()
        quit_driver()
        next_steps()
        quit_driver()
        try:
            shutil.copytree(session_path, backup_path, dirs_exist_ok=True)
            output("We backed up the session data in case of a later crash!",3)
        except Exception as e:
            output("Oops, we weren't able to make a backup of the session data! Error:", 1)

        output("\nCHROME DRIVER DETACHED: It is safe to stop the script if you want to.\n",2)
        pm2_session = session_path.replace("./selenium/", "")
        output(f"You could add the new/updated session to PM use: pm2 start claim.py --name {pm2_session} -- {pm2_session}",1)
        user_choice = input("Enter 'y' to continue to 'claim' function, 'n' to exit or 'a' to add in PM2: ").lower()
        if user_choice == "n":
            output("Exiting script. You can resume the process later.",1)
            sys.exit()
        if user_choice == "a":
            start_pm2_app("claim.py", pm2_session, pm2_session)
            user_choice = input("Should we save your PM2 processes? (y, or enter to skip): ").lower()
            if user_choice == "y":
                save_pm2()
            output(f"You can now watch the session log into PM2 with: pm2 logs {pm2_session}",2)
            sys.exit()

    while True:
        manage_session()
        wait_time = full_claim()

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
        output("\nCHROME DRIVER DETACHED: It is safe to stop the script if you want to.\n",1)
        
        now = datetime.now()
        next_claim_time = now + timedelta(minutes=wait_time)
        next_claim_time_str = next_claim_time.strftime("%H:%M")
        output(f"Need to wait until {next_claim_time_str} before the next claim attempt. Approximately {wait_time} minutes.",1)

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
