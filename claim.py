import os
import sys
import time
from datetime import datetime, timedelta
import re
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

# Initiate global variables then set up paths and session data:
forceClaim = False
debugIsOn = False
hideSensitiveInput = True
screenshotQRCode = True

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

# Update the settings based on user input
update_settings()

# Ask the user for a unique session ID
user_input = input("Enter your unique Session Name here, or hit <enter> for the next sequential folder: ")
user_input = user_input.strip()

# Check directories in the screenshots directory to find the next numeric session ID
screenshots_dir = "./screenshots/"
dir_contents = os.listdir(screenshots_dir)
numeric_dirs = [dir_name for dir_name in dir_contents if dir_name.isdigit() and os.path.isdir(os.path.join(screenshots_dir, dir_name))]
next_session_id = "1"
if numeric_dirs:
    highest_numeric_dir = max(map(int, numeric_dirs))
    next_session_id = str(highest_numeric_dir + 1)

# If user input is null, set it to the next available numeric session ID
if not user_input:
    user_input = next_session_id

session_path = "./selenium/{}".format(user_input)
os.makedirs(session_path, exist_ok=True)
screenshots_path = "./screenshots/{}".format(user_input)
os.makedirs(screenshots_path, exist_ok=True)
print(f"Our screenshot path is {screenshots_path}")

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
    chrome_options.add_argument("--incognito") # Allows for multiple HereWallet accounts from a single TG account
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

# Create a separate function for WebDriver setup for flexibility and error handling
driver = setup_driver(chromedriver_path) 

time.sleep(1)
wait = WebDriverWait(driver, 10)

def log_into_telegram():
    driver.get("https://web.telegram.org/k/#@herewalletbot")

    print("*** Important: Having @HereWalletBot open in your Telegram App might stop this script loggin in! ***")
    
    # QR Code Method
    if screenshotQRCode:
        try:
          wait = WebDriverWait(driver, 20)  # Wait up to 20 seconds for the QR canvas
          qr_canvas_xpath = "//canvas[@class='qr-canvas']"
          qr_canvas = wait.until(EC.presence_of_element_located((By.XPATH, qr_canvas_xpath))) 
          # We've successfully found the QR code canvas
          time.sleep(5)
          driver.save_screenshot("{}/00_take_QR_Code_Screenshot.png".format(screenshots_path))
          print ("The screenshot has now been saved in your screenshots folder: {}".format(screenshots_path))
          input('Hit enter after you scanned the QR code in Settings -> Devices -> Link Desktop Device:')
          driver.get("https://web.telegram.org/k/#@herewalletbot")

          try:
            print ("Validating the QR Code...")
            wait = WebDriverWait(driver, 30)  # Assuming the login screen might take time
            chat_xpath = "//div[contains(@class, 'input-message-input')]"
            chat_input = wait.until(EC.element_to_be_clickable((By.XPATH, chat_xpath)))
            print("QR Code Sucessfully Accepted!")
            # Successful login using QR code
            return  

          except TimeoutException:
            print("Timeout: Restart the script and retry the QR Code or switch to the OTP method.")

        except TimeoutException:
          print("Canvas not found: Restart the script and retry the QR Code or switch to the OTP method.")

    # OTP Login Method
    print("Attempting to load the OTP method...")
    driver.get("https://web.telegram.org/k/#@herewalletbot")
    wait = WebDriverWait(driver, 30)
    login_button_xpath = "//button[contains(@class, 'btn-primary') and contains(., 'Log in by phone Number')]"
    login_button = wait.until(EC.element_to_be_clickable((By.XPATH, login_button_xpath)))
    if debugIsOn:
        driver.save_screenshot("{}/01_Login_By_Phone_Number.png".format(screenshots_path))
    login_button.click()

    # Country Code Selection
    wait = WebDriverWait(driver, 20)
    country_code_dropdown_xpath = "//div[@class='input-field-input']//span[@class='i18n']"    
    country_code_dropdown = wait.until(EC.element_to_be_clickable((By.XPATH, country_code_dropdown_xpath)))
    if debugIsOn:
        driver.save_screenshot("{}/02_Country_Code_Confirmation.png".format(screenshots_path))
    user_input = input("Please enter your Country Name as it appears in the Telegram list: ").strip()
    country_code_dropdown.click()  
    country_code_dropdown.send_keys(user_input)
    country_code_dropdown.send_keys(Keys.RETURN) 

    # Phone Number Input
    wait = WebDriverWait(driver, 20)
    phone_number_input_xpath = "//div[@class='input-field-input' and @inputmode='decimal']"
    phone_number_input = wait.until(EC.element_to_be_clickable((By.XPATH, phone_number_input_xpath)))
    if hideSensitiveInput:
        user_phone = getpass.getpass("Please enter your phone number without leading 0 (hidden input): ")
    else:
        user_phone = input("Please enter your phone number without leading 0 (visible input): ")
    phone_number_input.click() 
    phone_number_input.send_keys(user_phone)

    # Wait for the "Next" button to be clickable and click it

    
    wait = WebDriverWait(driver, 20)
    next_button_xpath = "//button[contains(@class, 'btn-primary') and .//span[contains(text(), 'Next')]]"
    next_button = wait.until(EC.visibility_of_element_located((By.XPATH, next_button_xpath)))
    if debugIsOn:
        driver.save_screenshot("{}/03_Ready_To_Click_Next.png".format(screenshots_path))
    next_button.click()

    try:
        # Attempt to locate and interact with the OTP field
        wait = WebDriverWait(driver, 20)
        password = wait.until(EC.element_to_be_clickable((By.XPATH, "//input[@type='tel']")))
        if debugIsOn:
            time.sleep(3)
            driver.save_screenshot("{}/04_Ready_for_OTP.png".format(screenshots_path))
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
        time.sleep(3)
        driver.save_screenshot("{}/05_After_Entering_OTP.png".format(screenshots_path))

def next_steps():
    driver.get("https://web.telegram.org/k/#@herewalletbot")

    # There is a very unlikely scenario that the chat might have been cleared.
    # In this case, the "START" button needs pressing to expose the chat window!
    wait = WebDriverWait(driver, 5)
    print("Looking for the 'START' button which is only present on first launch...")
    try:
        fl_xpath = "//button[contains(., 'START')]"
        fl_button = wait.until(EC.element_to_be_clickable((By.XPATH, fl_xpath)))
        actions = ActionChains(driver)
        actions.move_to_element(fl_button).pause(0.2).perform()
        driver.execute_script("arguments[0].click();", fl_button)
        print("Clicked the START button.")
    except TimeoutException:
        print("As expected, the START button was not found at this time.")

    # Let's look for the central tab and send the /start command
    if debugIsOn:
        time.sleep(3)
        driver.save_screenshot("{}/06_Look_To_Start_HereWallet_App.png".format(screenshots_path))

    print("Sending the '/start' command to the central console...")
    driver.get("https://web.telegram.org/k/#@herewalletbot")
    WebDriverWait(driver, 30).until(lambda d: d.execute_script('return document.readyState') == 'complete')
    try:
        wait = WebDriverWait(driver, 30)
        chat_xpath = "//div[contains(@class, 'input-message-container')]/div[contains(@class, 'input-message-input')][1]"
        chat_input = wait.until(EC.presence_of_element_located((By.XPATH, chat_xpath)))
        print("Input Message Container is valid...")
        # actions = ActionChains(driver)
        # actions.move_to_element(chat_input).pause(0.2).perform()
        driver.execute_script("arguments[0].click();", chat_input)
        chat_input.send_keys("/start")
        chat_input.send_keys(Keys.RETURN)
        print("Successfully sent the '/start' command.")
        
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
                driver.save_screenshot("{}/07_Open_Launch_Popup.png".format(screenshots_path))
            actions.perform()
            driver.execute_script("arguments[0].click();", button)
            clicked = True
            break
        except StaleElementReferenceException:
            continue
        except ElementClickInterceptedException:
            continue
    if not clicked:
        print("None of the 'Open Wallet' buttons were clickable.")
    else:
        print ("The link to open the app was sucessfully clicked.")

    # Now let's move to and JS click the "Launch" Button
    wait = WebDriverWait(driver, 20)
    launch_app_xpath = "//button[contains(@class, 'popup-button') and contains(., 'Launch')]"
    launch_app_button = wait.until(EC.element_to_be_clickable((By.XPATH, launch_app_xpath)))
    actions = ActionChains(driver)
    actions.move_to_element(launch_app_button).pause(0.2)
    actions.perform()
    time.sleep(2)
    driver.execute_script("arguments[0].click();", launch_app_button)
    if debugIsOn:
        driver.save_screenshot("{}/08_Launch_Button_to_Click.png".format(screenshots_path))

    # HereWalletBot Pop-up Handling
    try:
        # Let's try to switch focus to the iFrame.
        wait = WebDriverWait(driver, 120)
        print("Initialising HereWalletBot pop-up window...")
        popup_body = wait.until(EC.presence_of_element_located((By.CLASS_NAME, "popup-body")))
        iframe = popup_body.find_element(By.TAG_NAME, "iframe")
        driver.switch_to.frame(iframe)
        print("Successfully switched to the iframe...")

        # Attempt to interact with elements within the iframe.
        # Let's click the login button first:
        wait = WebDriverWait(driver, 120)
        login_button_xpath = "//p[contains(text(), 'Log in')]"
        login_button = wait.until(EC.element_to_be_clickable((By.XPATH, login_button_xpath)))
        if debugIsOn:
            driver.save_screenshot("{}/08b_Found_Login_Button.png".format(screenshots_path))
        actions = ActionChains(driver)
        actions.move_to_element(login_button).pause(0.2).click().perform()
        print("Clicked log in button...")

        # Then look for the seed phase textarea:
        wait = WebDriverWait(driver, 120)
        input_field = wait.until(EC.element_to_be_clickable((By.XPATH, "//*[@id=\"root\"]//p[contains(text(), 'Seed or private key')]/ancestor-or-self::*/textarea")))
        if debugIsOn:
            driver.save_screenshot("{}/08c_Enter_Seed_Phrase.png".format(screenshots_path))
        print("Found seed phrase text area...")

        # Paste in the seed phase (debug screenshot removed for production version):
        actions = ActionChains(driver)
        actions.move_to_element(input_field).pause(0.2).click().send_keys(validate_seed_phrase()).perform() 
        print("Entered the seed phrase...")

        # Click the continue button after seed phrase entry:
        continue_button = wait.until(EC.element_to_be_clickable((By.XPATH, "//button[contains(text(), 'Continue')]")))
        actions = ActionChains(driver)
        actions.move_to_element(continue_button).pause(0.2).click().perform() 
        print("Clicked continue button after seed phrase entry (loading app, please be patient)...")

        # Click the account selection button:
        wait = WebDriverWait(driver, 120)
        select_account = wait.until(EC.element_to_be_clickable((By.XPATH, "//button[contains(text(), 'Select account')]")))
        if debugIsOn:
            driver.save_screenshot("{}/08e_Account_Selection_Screen.png".format(screenshots_path))
        actions = ActionChains(driver)
        actions.move_to_element(select_account).pause(0.2).click().perform()

        # Click on the Storage link:
        storage = wait.until(EC.element_to_be_clickable((By.XPATH, "//h4[text()='Storage']")))
        actions = ActionChains(driver)
        actions.move_to_element(storage).pause(0.2).perform()
        driver.execute_script("arguments[0].click();", storage)
        print("Selecting the 'storage' page...")

        if debugIsOn:
            print("\nWe appear to have correctly navigated to the storage page.\nHanding over to the Claim function :)\n")
            time.sleep(3)
            driver.save_screenshot("{}/08f_After_Selecting_Storage.png".format(screenshots_path))


    except TimeoutException:
        print("Failed to find or switch to the iframe within the timeout period.")

    except Exception as e:
        print(f"An error occurred: {e}")

def claim():
    print ("\nStarting a new cycle of the Claim function...\n")
    if debugIsOn:
            driver.save_screenshot("{}/09a_Start_of_Claim_function.png".format(screenshots_path))

    try:
        # Let's see how long until the wallet is ready to collected.
        wait = WebDriverWait(driver, 120)
        wait_time_xpath = "//div[contains(., 'Storage')]//p[contains(., 'Filled') or contains(., 'to fill')]"
        wait_time_element = wait.until(EC.visibility_of_element_located((By.XPATH, wait_time_xpath)))
        if debugIsOn:
            driver.save_screenshot("{}/09b_Found_the_Wait_Time_function.png".format(screenshots_path))
            print ("Found the current wait time countdown...")
        wait_time_text = wait_time_element.text
    except TimeoutException:
        print("Could not find the wait time element within the specified time.")
        wait_time_text = "Unknown"

    try:
        print("The pre-claim wait time is : {}".format(wait_time_text))
        if wait_time_text == "Filled" or forceClaim:
            try:
                # First, try to click "Check NEWS" button if it exists
                wait = WebDriverWait(driver, 10)
                if debugIsOn:
                    print("Checking for news to read...")
                original_window = driver.current_window_handle
                check_news_button_xpath = "//button[contains(text(), 'Check NEWS')]"
                check_news_button = wait.until(EC.element_to_be_clickable((By.XPATH, check_news_button_xpath)))
                actions = ActionChains(driver)
                actions.move_to_element(check_news_button).pause(0.2).click().perform() 
                driver.switch_to.window(original_window)
                if debugIsOn:
                    print("News checked. Waiting for claim button...")
                    driver.save_screenshot("{}/09c_after_checking_news_Seed.png".format(screenshots_path))
            except TimeoutException:
                if debugIsOn:
                    print("No news to check or button not found.")

            try:
                # Let's double check if we have to reselect the iFrame after news
                try:
                    wait = WebDriverWait(driver, 120)
                    popup_body = wait.until(EC.presence_of_element_located((By.CLASS_NAME, "popup-body")))
                    iframe = popup_body.find_element(By.TAG_NAME, "iframe")
                    driver.switch_to.frame(iframe)

                except NoSuchElementException as e:
                    print(f"Iframe not found within popup_body: {e}")

                except Exception as e:
                    if debugIsOn:
                        print("It looks like there was no news to read.")
                
                wait = WebDriverWait(driver, 120)
                # Click on the "Claim HOT" button:
                claim_HOT_button_xpath = "//button[contains(text(), 'Claim HOT')]"
                claim_HOT_button = wait.until(EC.element_to_be_clickable((By.XPATH, claim_HOT_button_xpath)))
                if debugIsOn:
                    print("Claim button found...")
                    driver.save_screenshot("{}/9d_Claim_button_found.png".format(screenshots_path))
                actions = ActionChains(driver)
                actions.move_to_element(claim_HOT_button).pause(0.2).click().perform() 
                print ("Claim button clicked...")

                # Now let's try again to get the time remaining until filled. 
                wait = WebDriverWait(driver, 120)
                wait_time_xpath = "//div[contains(., 'Storage')]//p[contains(., 'to fill')]"
                wait_time_element = wait.until(EC.visibility_of_element_located((By.XPATH, wait_time_xpath)))
                if debugIsOn:
                    driver.save_screenshot("{}/9f_wait_time_found.png".format(screenshots_path))
                wait_time_text = wait_time_element.text

                # Extract time until the "Storage" pot is full again:
                time.sleep(15)
                matches = re.findall(r'(\d+)([hm])', wait_time_text)
                total_wait_time = sum(int(value) * (60 if unit == 'h' else 1) for value, unit in matches)
                total_wait_time += 1
                print("Claim attempted. Post claim raw wait time: %s & proposed new wait timer = %s minutes." % (wait_time_text, total_wait_time))
                if debugIsOn:
                    driver.save_screenshot("{}/9g_after_get_time_remaining.png".format(screenshots_path))
                return max(60, total_wait_time)  # Wait a minimum one hour or the new wait timer. 

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
    clear_screen()
    print("Starting the login process...")
    log_into_telegram()
    next_steps()
    while True:
        wait_time = claim()
        global forceClaim
        forceClaim = False
        now = datetime.now()
        next_claim_time = now + timedelta(minutes=wait_time)
        next_claim_time_str = next_claim_time.strftime("%H:%M")
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
