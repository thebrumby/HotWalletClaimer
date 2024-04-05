import os
import shutil
import sys
import time
import re
import json
import getpass
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

# Initiate global variables then set up paths and session data:
forceClaim = False
debugIsOn = False
hideSensitiveInput = True
screenshotQRCode = True
logPM2Messages = False
driver = None
target_element = None

print("Initialising the HOT Wallet Auto-claim Python Script - Good Luck!")

# Format the session_path with the user's input
user_input = ""
session_path = "./selenium/{}".format(user_input)
os.makedirs(session_path, exist_ok=True)
screenshots_path = "./screenshots/{}".format(user_input)
os.makedirs(screenshots_path, exist_ok=True)
print(f"Our screenshot path is {screenshots_path}")

# Prompt the user to modify settings
def update_settings():
    global forceClaim, debugIsOn, screenshotQRCode

    # Force a claim on first run
    force_claim_response = input("Shall we force a claim on first run? (Y/N, default = N): ").strip().lower()
    if force_claim_response == "y":
        forceClaim = True
    else:
        forceClaim = False

    # Enable debugging
    debug_response = input("Should we enable debugging? (Y/N, default = N): ").strip().lower()
    if debug_response == "y":
        debugIsOn = True
    else:
        debugIsOn = False

    # Allow log in by QR code
    qr_code_response = input("Shall we allow log in by QR code? (Y/N, default = Y): ").strip().lower()
    if qr_code_response == "n":
        screenshotQRCode = False
    else:
        screenshotQRCode = True

def add_status_message(message):
    """Prepend a status message to pm2_updates.txt with a timestamp."""
    datetime_now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    full_message = f"{datetime_now} - {message}\n"
    
    # Check if the file exists and read its content
    if os.path.isfile(status_file_path):
        with open(status_file_path, 'r') as file:
            content = file.read()
    else:
        content = ""
    
    # Prepend the new message and write everything back
    with open(status_file_path, 'w') as file:
        file.write(full_message + content)

def log_next_claim_attempt(next_claim_time, wait_time_minutes):
    """Log message about next claim attempt."""
    next_claim_time_str = next_claim_time.strftime("%Y-%m-%d %H:%M:%S")
    message = f"Need to wait until {next_claim_time_str} before the next claim attempt. Approximately {wait_time_minutes} minutes."
    add_status_message(message)
    print(message)

def get_session_id():
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
        print(f"Session ID provided: {user_input}")
        # Safely check for a second argument
        if len(sys.argv) > 2 and sys.argv[2] == "verbose":
            logPM2Messages = True
else:
    update_settings()
    user_input = get_session_id()


session_path = "./selenium/{}".format(user_input)
os.makedirs(session_path, exist_ok=True)
screenshots_path = "./screenshots/{}".format(user_input)
os.makedirs(screenshots_path, exist_ok=True)
print(f"Our screenshot path is {screenshots_path}")
status_file_name = "pm2_updates.txt"
status_file_path = os.path.join(screenshots_path, status_file_name)

# Define our base path for debugging screenshots
screenshot_base = os.path.join(screenshots_path, "screenshot")

# Echo the Status to screen.
if forceClaim:
    print("forceClaim is enabled. We will attempt to process a claim even if the pot is not yet at minimum.")
else:
    print("forceClaim is disabled. We will wait for the timer to elapse and the storage pot to be full.")

if debugIsOn:
    print("Debugging is enabled. Screenshots will be saved on your local drive in the specified folder.")
else:
    print("Debugging is disabled. No screenshots will be taken.")

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
        print(f"Initial ChromeDriver setup may have failed: {e}")
        print("Please ensure you have the correct ChromeDriver version for your system.")
        print("If you copied the GitHub commands, ensure all lines executed.")
        print("Visit https://chromedriver.chromium.org/downloads to find the right version.")
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
 
def log_into_telegram():
    global driver, target_element, debugIsOn, session_path, screenshots_path

    if os.path.exists(session_path):
        shutil.rmtree(session_path)
    os.makedirs(session_path, exist_ok=True)
    if os.path.exists(screenshots_path):
        shutil.rmtree(screenshots_path)
    os.makedirs(screenshots_path, exist_ok=True)

    driver = get_driver()
    driver.get("https://web.telegram.org/k/#@herewalletbot")

    print(f"Our screenshot path is {screenshots_path}\n")
    print("*** Important: Having @HereWalletBot open in your Telegram App might stop this script loggin in! ***\n")
    
    # QR Code Method
    if screenshotQRCode:
        try:
          WebDriverWait(driver, 30).until(lambda d: d.execute_script('return document.readyState') == 'complete')
          xpath = "//canvas[@class='qr-canvas']"
          move_and_click(xpath, 30, False, "check for visibility of QR code canvas (Validate QR code)", "00a", "visible")
          driver.save_screenshot("{}/00 - Initial QR code.png".format(screenshots_path))
          print ("The screenshot has now been saved in your screenshots folder: {}".format(screenshots_path))
          input('Hit enter after you scanned the QR code in Settings -> Devices -> Link Desktop Device:')
          try:
            print ("Validating the QR Code (30 seconds wait if not valid)...\n")
            driver.get("https://web.telegram.org/k/#@herewalletbot")
            WebDriverWait(driver, 30).until(lambda d: d.execute_script('return document.readyState') == 'complete')
            xpath = "//canvas[@class='qr-canvas']"
            move_and_click(xpath, 30, False, "check if logged in (Validate QR code)", "00b", "invisible")
            # Successful login using QR code
            return

          except TimeoutException:
            print("Timeout: Restart the script and retry the QR Code or wait for the OTP method.")

        except TimeoutException:
          print("Canvas not found: Restart the script and retry the QR Code or switch to the OTP method.")

    # OTP Login Method
    print("Attempting to load the OTP method...")
    driver.get("https://web.telegram.org/k/#@herewalletbot")
    xpath = "//button[contains(@class, 'btn-primary') and contains(., 'Log in by phone Number')]"
    move_and_click(xpath, 30, True, "switch to log in by phone number", "01a", "clickable")

    # Country Code Selection
    xpath = "//div[@class='input-field-input']//span[@class='i18n']"    
    target_element = move_and_click(xpath, 30, True, "update users country (OTP Method)", "01b", "clickable")
    user_input = input("Please enter your Country Name as it appears in the Telegram list: ").strip()  
    target_element.send_keys(user_input)
    target_element.send_keys(Keys.RETURN) 

    # Phone Number Input
    xpath = "//div[@class='input-field-input' and @inputmode='decimal']"
    target_element = move_and_click(xpath, 30, True, "enter users phone number (OTP Method)", "01c", "clickable")
    if hideSensitiveInput:
        user_phone = getpass.getpass("Please enter your phone number without leading 0 (hidden input): ")
    else:
        user_phone = input("Please enter your phone number without leading 0 (visible input): ")
    target_element.send_keys(user_phone)

    # Wait for the "Next" button to be clickable and click it    
    xpath = "//button[contains(@class, 'btn-primary') and .//span[contains(text(), 'Next')]]"
    move_and_click(xpath, 30, True, "click next and proceed to OTP entry (OTP Method)", "01d", "visible")

    try:
        # Attempt to locate and interact with the OTP field
        wait = WebDriverWait(driver, 20)
        password = wait.until(EC.element_to_be_clickable((By.XPATH, "//input[@type='tel']")))
        if debugIsOn:
            time.sleep(3)
            driver.save_screenshot("{}/01e_Ready_for_OTP.png".format(screenshots_path))
        otp = input("What is the Telegram OTP from your app? ")
        password.click()
        password.send_keys(otp)
        clear_screen()
        print("Let's try to log in using your Telegram OTP. Please Wait.")

    except TimeoutException:
        # OTP field not found 
        print("OTP entry has failed - maybe you entered the wrong code, or possible flood cooldown issue.")

    except Exception as e:  # Catch any other unexpected errors
        print("Login failed. Error:", e) 
        if debugIsOn:
            driver.save_screenshot("{}/01-error_Something_Occured.png".format(screenshots_path))
    
    if debugIsOn:
        time.sleep(3)
        driver.save_screenshot("{}/01f_After_Entering_OTP.png".format(screenshots_path))
    
def next_steps():
    global driver, target_element, debugIsOn
    driver = get_driver()
    driver.get("https://web.telegram.org/k/#@herewalletbot")
    WebDriverWait(driver, 30).until(lambda d: d.execute_script('return document.readyState') == 'complete')

    # There is a very unlikely scenario that the chat might have been cleared.
    # In this case, the "START" button needs pressing to expose the chat window!
    wait = WebDriverWait(driver, 5)
    print("Looking for the 'START' button which is only present on first launch...")
    xpath = "//button[contains(., 'START')]"
    move_and_click(xpath, 5, True, "check for the start button (if chat has been reset)", "02", "clickable")

    # Look for the center console and send the /start command. 
    driver.get("https://web.telegram.org/k/#@herewalletbot")
    WebDriverWait(driver, 30).until(lambda d: d.execute_script('return document.readyState') == 'complete')
    try:
        xpath = "//div[contains(@class, 'input-message-container')]/div[contains(@class, 'input-message-input')][1]"
        chat_input = move_and_click(xpath, 30, False, "look for the central message box", "03", "present")
        if chat_input:  # Ensure chat_input is not None
            if debugIsOn:
                print("Input Message Container is valid...")
            chat_input.send_keys("/start")
            chat_input.send_keys(Keys.RETURN)
            print("Successfully sent the '/start' command.\n")
        else:
            print("Failed to find the message input box.\n")
        
    except TimeoutException:
        # Unable to enter the start command
        print("Unable to send the '/start' command.  Possible causes might be:")
        print("- You used the OTP method and it didn't take.")
        print("- You can always try deleting the chat with @HereWalletBot in your Telegram app and try again.")
        print("- Check GitHub for a code update!")
    except ElementClickInterceptedException:
        print("Error: The message box might be blocked by another element.")
    except Exception as e:  # Catch other potential errors
        print(f"An error occurred during interaction: {e}")

    # Now let's try to find a working link to open the launch button
    start_app_xpath = "//a[@href='https://t.me/herewalletbot/app']"
    start_app_buttons = wait.until(EC.presence_of_all_elements_located((By.XPATH, start_app_xpath)))
    clicked = False
    print ("Looking for a link to open the app...")
    for button in reversed(start_app_buttons):
        actions = ActionChains(driver)
        actions.move_to_element(button).pause(0.2)
        try:
            if debugIsOn:
                driver.save_screenshot("{}/04_Open_Launch_Popup.png".format(screenshots_path))
            actions.perform()
            driver.execute_script("arguments[0].click();", button)
            clicked = True
            break
        except StaleElementReferenceException:
            continue
        except ElementClickInterceptedException:
            continue
    if not clicked:
        print("None of the 'Open Wallet' buttons were clickable.\n")
    else:
        print ("The link to open the app was sucessfully clicked.\n")

    # Now let's move to and JS click the "Launch" Button
    xpath = "//button[contains(@class, 'popup-button') and contains(., 'Launch')]"
    move_and_click(xpath, 30, True, "click the 'Launch' button", "05", "clickable")

    # HereWalletBot Pop-up Handling
    try:
            # HereWalletBot Pop-up Handling
        try:
            # Let's try to switch focus to the iFrame.
            wait = WebDriverWait(driver, 120)
            print("Initialising HereWalletBot pop-up window...")
            popup_body = wait.until(EC.presence_of_element_located((By.CLASS_NAME, "popup-body")))
            iframe = popup_body.find_element(By.TAG_NAME, "iframe")
            driver.switch_to.frame(iframe)
            print("Successfully switched to the iframe...\n")
        except TimeoutException:
            print("Failed to find or switch to the iframe within the timeout period.\n")

        # Attempt to interact with elements within the iframe.
        # Let's click the login button first:
        xpath = "//p[contains(text(), 'Log in')]"
        move_and_click(xpath, 30, True, "log into HereWallet", "06", "clickable")

        # Then look for the seed phase textarea:
        xpath = "//*[@id=\"root\"]//p[contains(text(), 'Seed or private key')]/ancestor-or-self::*/textarea"
        input_field = move_and_click(xpath, 30, True, "enter seedphrase", "07", "clickable")
        input_field.send_keys(validate_seed_phrase()) 
        print("Entered the seed phrase...")

        # Click the continue button after seed phrase entry:
        xpath = "//button[contains(text(), 'Continue')]"
        move_and_click(xpath, 30, True, "continue after seedphrase entry", "08", "clickable")

        # Click the account selection button:
        xpath = "//button[contains(text(), 'Select account')]"
        move_and_click(xpath, 120, True, "continue at account selection screen", "09", "clickable")

        # Click on the Storage link:
        xpath = "//h4[text()='Storage']"
        move_and_click(xpath, 30, True, "select the storage link in the game", "10", "clickable")
        print ("We appear to be logged in, let's save the cookies.")
        cookies_path = f"{session_path}/cookies.json"
        cookies = driver.get_cookies()
        with open(cookies_path, 'w') as file:
            json.dump(cookies, file)

        if debugIsOn:
            print("\nWe appear to have correctly navigated to the storage page.\nHanding over to the Claim function :)\n")
            time.sleep(3)
            driver.save_screenshot("{}/11-Sign In Process Complete.png".format(screenshots_path))


    except TimeoutException:
        print("Failed to find or switch to the iframe within the timeout period.")

    except Exception as e:
        print(f"An error occurred: {e}")

def claim():
    global driver, target_element, debugIsOn
    driver = get_driver()
    print ("\nStarting a new cycle of the Claim function...\n")
    driver.get("https://web.telegram.org/k/#@herewalletbot")
    WebDriverWait(driver, 30).until(lambda d: d.execute_script('return document.readyState') == 'complete')

    if debugIsOn:
        time.sleep(3)
        driver.save_screenshot("{}/100_Initial_Claim_Launch.png".format(screenshots_path))

    # There is a very unlikely scenario that the chat might have been cleared.
    # In this case, the "START" button needs pressing to expose the chat window!
    xpath = "//button[contains(., 'START')]"
    move_and_click(xpath, 5, True, "check for the start button (if chat has been reset)", "101", "clickable")

    # Look for the center console and send the /start command. 
    driver.get("https://web.telegram.org/k/#@herewalletbot")
    WebDriverWait(driver, 30).until(lambda d: d.execute_script('return document.readyState') == 'complete')
    try:
        xpath = "//div[contains(@class, 'input-message-container')]/div[contains(@class, 'input-message-input')][1]"
        chat_input = move_and_click(xpath, 30, False, "look for the central message box", "102", "present")
        if chat_input:  # Ensure chat_input is not None
            if debugIsOn:
                print("Input Message Container is valid...")
            chat_input.send_keys("/start")
            chat_input.send_keys(Keys.RETURN)
            print("Successfully sent the '/start' command.\n")
        else:
            print("Failed to find the message input box.\n")
    except TimeoutException:
        # Unable to enter the start command
        print("Unable to send the '/start' command.  Possible causes might be:")
        print("- You used the OTP method and it didn't take.")
        print("- You can always try deleting the chat with @HereWalletBot in your Telegram app and try again.")
        print("- Check GitHub for a code update!")
    except ElementClickInterceptedException:
        print("Error: The message box might be blocked by another element.")
    except Exception as e:  # Catch other potential errors
        print(f"An error occurred during interaction: {e}")

    # Now let's try to find a working link to open the launch button
    start_app_xpath = "//a[@href='https://t.me/herewalletbot/app']"
    wait = WebDriverWait(driver, 20)
    start_app_buttons = wait.until(EC.presence_of_all_elements_located((By.XPATH, start_app_xpath)))
    clicked = False
    print ("Looking for a link to open the app...")
    for button in reversed(start_app_buttons):
        actions = ActionChains(driver)
        actions.move_to_element(button).pause(0.2)
        try:
            if debugIsOn:
                driver.save_screenshot("{}/04_Open_Launch_Popup.png".format(screenshots_path))
            actions.perform()
            driver.execute_script("arguments[0].click();", button)
            clicked = True
            break
        except StaleElementReferenceException:
            continue
        except ElementClickInterceptedException:
            continue
    if not clicked:
        print("None of the 'Open Wallet' buttons were clickable.\n")
    else:
        print ("The link to open the app was sucessfully clicked.\n")

    # Now let's move to and JS click the "Launch" Button
    xpath = "//button[contains(@class, 'popup-button') and contains(., 'Launch')]"
    move_and_click(xpath, 30, True, "click the 'Launch' button", "104", "clickable")

    # HereWalletBot Pop-up Handling
    try:
        # Let's try to switch focus to the iFrame.
        wait = WebDriverWait(driver, 120)
        print("Initialising HereWalletBot pop-up window...")
        popup_body = wait.until(EC.presence_of_element_located((By.CLASS_NAME, "popup-body")))
        iframe = popup_body.find_element(By.TAG_NAME, "iframe")
        driver.switch_to.frame(iframe)
        print("Successfully switched to the iframe...\n")
    except TimeoutException:
        print("Failed to find or switch to the iframe within the timeout period.\n")

    except Exception as e:
        print(f"An error occurred: {e}")

    # Click on the Storage link:
    xpath = "//h4[text()='Storage']"
    move_and_click(xpath, 30, True, "clicking on the storage button", "105", "clickable")

    try:
        # Let's see how long until the wallet is ready to collected.
        xpath = "//div[contains(., 'Storage')]//p[contains(., 'Filled') or contains(., 'to fill')]"
        wait_time_element = move_and_click(xpath, 20, False, "get the pre-claim wait timer", "106", "visible")
        wait_time_text = wait_time_element.text
    except TimeoutException:
        print("Could not find the wait time element within the specified time.")
        wait_time_text = "Unknown"

    try:
        print("The pre-claim wait time is : {}".format(wait_time_text))
        if wait_time_text == "Filled" or forceClaim:
            try:
                original_window = driver.current_window_handle
                xpath = "//button[contains(text(), 'Check NEWS')]"
                move_and_click(xpath, 10, True, "check for NEWS.", "107", "clickable")
                driver.switch_to.window(original_window)
            except TimeoutException:
                if debugIsOn:
                    print("No news to check or button not found.")

            try:
                # Let's double check if we have to reselect the iFrame after news
                try:
                    wait = WebDriverWait(driver, 5)
                    popup_body = wait.until(EC.presence_of_element_located((By.CLASS_NAME, "popup-body")))
                    iframe = popup_body.find_element(By.TAG_NAME, "iframe")
                    driver.switch_to.frame(iframe)

                except NoSuchElementException as e:
                    print(f"Iframe not found within popup_body: {e}")

                except Exception as e:
                    # if debugIsOn:
                    print("It looks like there was no news to read.")
                
                # Click on the "Claim HOT" button:
                xpath = "//button[contains(text(), 'Claim HOT')]"
                move_and_click(xpath, 30, True, "click the claim button", "109", "clickable")

                # Now let's try again to get the time remaining until filled. 
                # 4th April 24 - Let's wait for the spinner to disappear before trying to get the new time to fill.
                print ("Let's wait for the pending Claim spinner to stop spinning...")
                time.sleep(5)
                wait = WebDriverWait(driver, 240)
                spinner_xpath = "//*[contains(@class, 'spinner')]" 
                try:
                    wait.until(EC.invisibility_of_element_located((By.XPATH, spinner_xpath)))
                    print("Pending action spinner has stopped...")
                except TimeoutException:
                    print("Looks like the site has lag- the Spinner did not disappear in time...")
                xpath = "//div[contains(., 'Storage')]//p[contains(., 'Filled') or contains(., 'to fill')]"
                wait_time_element = move_and_click(xpath, 20, False, "get the pre-claim wait timer", "110", "visible")
                wait_time_text = wait_time_element.text
                # Extract time until the "Storage" pot is full again:
                matches = re.findall(r'(\d+)([hm])', wait_time_text)
                total_wait_time = sum(int(value) * (60 if unit == 'h' else 1) for value, unit in matches)
                total_wait_time += 1
                print("Claim attempted. Post claim raw wait time: %s & proposed new wait timer = %s minutes." % (wait_time_text, total_wait_time))
                return max(60, total_wait_time)

            except TimeoutException:
                print("The claim process timed out: Maybe the site has lag? Will retry after one hour.")
                return 60
            except Exception as e:
                print(f"An error occurred while trying to claim: {e}\nLet's wait an hour and try again")
                return 60

        else:
            # If the wallet isn't ready to be claimed, calculate wait time based on the timer provided on the page
            matches = re.findall(r'(\d+)([hm])', wait_time_text)
            if matches:
                total_time = sum(int(value) * (60 if unit == 'h' else 1) for value, unit in matches)
                total_time += 1
                total_time = max(5, total_time) # Wait at least 5 minutes or the time
                print("Not Time to claim this wallet yet. Wait for {} Minutes will the storage is filled.".format(total_time))
                return total_time 
            else:
                print("No wait time data found? Let's check again in one hour.")
                return 60  # Default wait time when no specific time until filled is found.
    except Exception as e:
        print("An unexpected error occurred: {}".format(e))
        return 60  # Default wait time in case of an unexpected error

def clear_screen():
    # Attempt to clear the screen after entering the seed phrase or mobile phone number.
    # For Windows
    if os.name == 'nt':
        os.system('cls')
    # For macOS and Linux
    else:
        os.system('clear')

def move_and_click(xpath, wait_time, click, action_description, step, expectedCondition):
    global driver, screenshots_path, debugIsOn
    target_element = None
    failed = False
    print(f"Step {step} - Attempting to {action_description}...")
    try:
        wait = WebDriverWait(driver, wait_time)
        if expectedCondition == "visible":
            target_element = wait.until(EC.visibility_of_element_located((By.XPATH, xpath)))
        elif expectedCondition == "present":
            target_element = wait.until(EC.presence_of_element_located((By.XPATH, xpath)))
        elif expectedCondition == "invisible":
            wait.until(EC.invisibility_of_element_located((By.XPATH, xpath)))
            # For 'invisible', there's no element to return, but the function signifies the element is gone.
        elif expectedCondition == "clickable":
            target_element = wait.until(EC.element_to_be_clickable((By.XPATH, xpath)))
        else:
            print("The function wasn't called with a valid Expected Condition!")
        
        # Perform actions if the element is found and clicking is requested
        if click and target_element:
            try:
                actions = ActionChains(driver)
                actions.move_to_element(target_element).pause(0.2).click().perform()
                if debugIsOn:
                    print(f"Successfully clicked {action_description} using ActionChains.")
            except Exception as e:
                if debugIsOn:
                    print(f"ActionChains click failed. Attempting JavaScript click as fallback.")
                driver.execute_script("arguments[0].click();", target_element)
                if debugIsOn:
                    print(f"Successfully clicked {action_description} using JavaScript fallback.")
        if not failed:
            print(f"Step {step} - Successfully interacted with: {action_description}.\n")
        if debugIsOn:
            screenshot_path = f"{screenshots_path}/{step}-{action_description}.png"
            driver.save_screenshot(screenshot_path)
    except TimeoutException:
        print(f"Step {step} - nothing found to action.\n")
        if debugIsOn:
            screenshot_path = f"{screenshots_path}/{step}-{action_description}.png"
            driver.save_screenshot(screenshot_path)
    except Exception as e:
        print(f"Step {step} - An error occurred while attempting to: {action_description}: {e}\n")
        if debugIsOn:
            screenshot_path = f"{screenshots_path}/{step}-ERROR-{action_description}.png"
            driver.save_screenshot(screenshot_path)
    finally:
        # Always return target_element, even if it's None (indicating the element wasn't found or wasn't clickable)
        return target_element


def validate_seed_phrase():
    # Let's take the user inputed seed phrase and carry out basic validation
    while True:
        # Prompt the user for their seed phrase
        if hideSensitiveInput:
            seed_phrase = getpass.getpass("Please enter your 12-word seed phrase (your input is hidden): ")
        else:
            seed_phrase = input("Please enter your 12-word seed phrase (your input is visible): ")
        try:
            if not seed_phrase:
                raise ValueError("Seed phrase cannot be empty.")

            words = seed_phrase.split()
            if len(words) != 12:
                raise ValueError("Seed phrase must contain exactly 12 words.")

            pattern = r"^[a-z ]+$"
            if not all(re.match(pattern, word) for word in words):
                raise ValueError("Seed phrase can only contain lowercase letters and spaces.")
            return seed_phrase  # Return if valid

        except ValueError as e:
            print(f"Error: {e}")

def main():
    driver = get_driver()
    quit_driver()
    clear_screen()
    cookies_path = os.path.join(session_path, 'cookies.json')
    if os.path.exists(cookies_path):
        print("Resuming the previous session...")
    else:
        print("Starting the Telegram & HereWalletBot login process...")
        log_into_telegram()
        quit_driver()
        next_steps()
        quit_driver()
        # Let's now offer the option to stop here or carry on.
        user_choice = input("Enter 'y' to continue to 'claim' function or 'n' to exit and resume in PM2: ").lower()
        if user_choice == "n":
            print("Exiting script. You can resume the process using PM2.")
            sys.exit()
    while True:
        wait_time = claim()
        quit_driver()
        global forceClaim
        forceClaim = False
        now = datetime.now()
        next_claim_time = now + timedelta(minutes=wait_time)
        next_claim_time_str = next_claim_time.strftime("%H:%M")
        if logPM2Messages:
            log_next_claim_attempt(next_claim_time, wait_time)
        else:
            print(f"Need to wait until {next_claim_time_str} before the next claim attempt. Approximately {wait_time} minutes.")

        while wait_time > 0:
            this_wait = min(wait_time, 15)
            now = datetime.now()
            timestamp = now.strftime("%H:%M")
            print(f"[{timestamp}] Waiting for {this_wait} more minutes...")
            time.sleep(this_wait * 60)  # Convert minutes to seconds
            wait_time -= this_wait
            if wait_time > 0:
                print(f"Updated wait time: {wait_time} minutes left.")

if __name__ == "__main__":
    main()