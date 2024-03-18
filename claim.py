import os
import time
import re
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.keys import Keys
from selenium.common.exceptions import NoSuchElementException, TimeoutException

print("Initialising the HOT Wallet Auto-claim Python Script - Good Luck!")

# Initiate paths and variables
forceClaim = False
debug_is_on = False

# Ask the user for a unique session ID
user_input = input("If using Screen to create more than one instance, enter your unique session Name here: ")
user_input = user_input.strip()
# If user input is null, set it to "1"
if not user_input:
    user_input = "1"

# Format the session_path with the user's input
session_path = "./selenium/{}".format(user_input)
os.makedirs(session_path, exist_ok=True)
screenshots_path = "./screenshots/{}".format(user_input)
os.makedirs(screenshots_path, exist_ok=True)

# Echo the Status to screen.
if forceClaim:
    print("forceClaim is enabled. We will attempt to process a claim even if the pot is not yet at minimum.")
else:
    print("forceClaim is disabled. We will wait for the timer until the earliest pot is Filled")

if debug_is_on:
    print("Debugging is enabled. Screenshots will be saved on your local drive in the specified folder.")
else:
    print("Debugging is disabled. No screenshots will be taken.")

# Hardcode URL for the Telegram App
url = 'https://tgapp.herewallet.app/auth/import#tgWebAppData=user%3D%257B%2522id%2522%253A831612161%252C%2522first_name%2522%253A%2522John%2522%252C%2522last_name%2522%253A%2522Doe%2522%252C%2522username%2522%253A%2522j_doe%2522%252C%2522language_code%2522%253A%2522en%2522%252C%2522allows_write_to_pm%2522%253Atrue%257D&chat_instance%3D-1658397054350349435&chat_type%3Dsender&auth_date%3D1710122886&hash%3Da8ed62de9dc49dad96f3a46d8297046a51ad4587a625bcefcf611d06be2bf499&tgWebAppVersion=7.0&tgWebAppPlatform=web&tgWebAppBotInline=1&tgWebAppThemeParams=%7B%22bg_color%22%3A%22%23ffffff%22%2C%22button_color%22%3A%22%233390ec%22%2C%22button_text_color%22%3A%22%23ffffff%22%2C%22hint_color%22%3A%22%23707579%22%2C%22link_color%22%3A%22%2300488f%22%2C%22secondary_bg_color%22%3A%22%23f4f4f5%22%2C%22text_color%22%3A%22%23000000%22%2C%22header_bg_color%22%3A%22%23ffffff%22%2C%22accent_text_color%22%3A%22%233390ec%22%2C%22section_bg_color%22%3A%22%23ffffff%22%2C%22section_header_text_color%22%3A%22%233390ec%22%2C%22subtitle_text_color%22%3A%22%23707579%22%2C%22destructive_text_color%22%3A%22%23df3f40%22%7D'

def setup_driver(chromedriver_path):
    """Configures WebDriver with best practices and handles ChromeDriver compatibility"""

    service = Service(chromedriver_path)
    chrome_options = webdriver.ChromeOptions()
    chrome_options.add_argument("user-data-dir={}".format(session_path))
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--log-level=3")  # Set log level to suppress INFO and WARNING messages
    chrome_options.add_argument("--disable-bluetooth")
    chrome_options.add_argument("--mute-audio")
    chrome_options.add_argument("--incognito")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_experimental_option('excludeSwitches', ['enable-logging'])

    # Compatibility Handling:
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
    # Let's test if we can click start without logging in (Continuing existing session)
    try:
        wait = WebDriverWait(driver, 10) 
        open_wallet_button = wait.until(EC.element_to_be_clickable((By.XPATH, "//a[contains(@class, 'reply-markup-button') and contains(@href, 'https://t.me/herewalletbot/app')]")))
        print("Open Wallet button found. Exiting the function early.")
        return  # Exit the function early as the start button was found
    except TimeoutException:
        pass  # No action needed, continue to the next step

    # Continue with the login process if the start button wasn't found
    # The wait timer can be adjusted based on lag in the app. 
    wait = WebDriverWait(driver, 20)
    login_button_xpath = "//button[contains(@class, 'btn-primary') and contains(., 'Log in by phone Number')]"
    login_button = wait.until(EC.element_to_be_clickable((By.XPATH, login_button_xpath)))
    login_button.click()
    if debug_is_on:
        driver.save_screenshot("{}/01_take_QR_Code_Screenshot.png".format(screenshots_path))
    # Let's wait until the Country Code list is available 
    country_code_dropdown_xpath = '//*[@id="auth-pages"]/div/div[2]/div[2]/div/div[3]/div[1]/div[1]/span'    
    country_code_dropdown = WebDriverWait(driver, 20).until(EC.element_to_be_clickable((By.XPATH, country_code_dropdown_xpath)))
    # Prompt the user for their country name
    user_input = input("Please enter your country name as it appears in the telegram List: ")
    user_input = user_input.strip()
    # Click the dropdown to make it active (if necessary)
    country_code_dropdown.click()    
    # Send the country code to the dropdown. If the dropdown requires selection from options, use a different approach.
    country_code_dropdown.send_keys(user_input)
    country_code_dropdown.send_keys(Keys.RETURN)  # You might need to press ENTER to confirm the selection
    # Wait a bit for any potential page updates (adjust the sleep time as necessary)
    time.sleep(2)
    
    # Wait for the phone number input field to be clickable
    phone_number_input_xpath = '//*[@id="auth-pages"]/div/div[2]/div[2]/div/div[3]/div[2]/div[1]'
    phone_number_input = WebDriverWait(driver, 20).until(EC.element_to_be_clickable((By.XPATH, phone_number_input_xpath)))
    if debug_is_on:
        driver.save_screenshot("{}/02_After_Contry_Code_Confirmation.png".format(screenshots_path))
    # Prompt the user for their phone number
    user_phone = input("Please enter your phone number (without leading 0): ")
    # Click the input field to make it active (if necessary)
    phone_number_input.click()
     # Send the phone number to the input field
    phone_number_input.send_keys(user_phone)
    if debug_is_on:
        driver.save_screenshot("{}/03_Ready_To_Click_Next.png".format(screenshots_path))

    # Wait for the "Next" button to be clickable and click it
    next_button_xpath = '//*[@id="auth-pages"]/div/div[2]/div[2]/div/div[3]/button[1]'
    next_button = WebDriverWait(driver, 20).until(EC.element_to_be_clickable((By.XPATH, next_button_xpath)))
    next_button.click()

    time.sleep(3)
    if debug_is_on:
        driver.save_screenshot("{}/04_After_Clicking_Next.png".format(screenshots_path))

    try:
        # Attempt to locate and interact with the OTP field
        password = wait.until(EC.element_to_be_clickable((By.XPATH, '//*[@id="auth-pages"]/div/div[2]/div[4]/div/div[3]/div/input')))
        otp = input("What is the Telegram OTP from your app? ")
        password.send_keys(otp)
        print("Let's try to log in using your Telegram OPT. Please Wait.")

    except TimeoutException:
        # OTP field not found 
        print("OTP might not have been required or failed.")

    except Exception as e:  # Catch any other unexpected errors
        print("Login failed. Error:", e) 
    
    time.sleep(3)
    if debug_is_on:
        driver.save_screenshot("{}/05_After_Entering_OTP.png".format(screenshots_path))

def next_steps():
    driver.get("https://web.telegram.org/k/#@herewalletbot")
    time.sleep(3)
    wait = WebDriverWait(driver, 30)
    if debug_is_on:
        driver.save_screenshot("{}/06_Look_To_Start_HereWallet_App.png".format(screenshots_path))

    # Locate the chat input field and send "/start" command
    chat_xpath = "//div[contains(@class, 'input-message-input')]"
    chat_input = wait.until(EC.element_to_be_clickable((By.XPATH, chat_xpath)))
    chat_input.send_keys("/start")
    chat_input.send_keys(Keys.RETURN)  # Press Enter to send the command
    time.sleep(3)
    if debug_is_on:
        driver.save_screenshot("{}/07_Start_App.png".format(screenshots_path))
   

    # Wait for the "Open Wallet" button to become clickable after sending "/start" and then click it
    start_app_xpath = start_app_xpath = "//div[contains(@class, 'reply-markup-row')]//a[contains(@class, 'reply-markup-button') and contains(., 'Open Wallet')]"
    start_app_button = wait.until(EC.element_to_be_clickable((By.XPATH, start_app_xpath)))
    driver.execute_script("arguments[0].click();", start_app_button)
    time.sleep(3)
    if debug_is_on:
        driver.save_screenshot("{}/08_Launch_Button.png".format(screenshots_path))

    # Wait for the "Launch" button to become clickable and then click it
    launch_app_xpath = "//button[contains(@class, 'popup-button') and contains(., 'Launch')]"
    launch_app_button = wait.until(EC.element_to_be_clickable((By.XPATH, launch_app_xpath)))
    driver.execute_script("arguments[0].click();", launch_app_button)
    time.sleep(3)
    if debug_is_on:
        driver.save_screenshot("{}/08a_Click_Launch_Button.png".format(screenshots_path))

    try:
        # Wait for the pop-up body to be present
        print("Initialising pop-up...")

        popup_body = WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.CLASS_NAME, "popup-body")))
        # Assuming the iframe is directly within the popup_body, switch to it
        iframe = popup_body.find_element(By.TAG_NAME, "iframe")
        driver.switch_to.frame(iframe)
        print("Switched to iFrame...")
        # Now attempt to interact with elements within the iframe
        # Example: Click a button identified by its XPath
        login_button_xpath = '//*[@id="root"]/div/button'
        login_button = WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.XPATH, login_button_xpath)))
        login_button.click()
        print("Clicked log in...")
        if debug_is_on:
            time.sleep(3)
            driver.save_screenshot("{}/08b_Clicked_Login_Button.png".format(screenshots_path))
        wait = WebDriverWait(driver, 60)
        input_field = wait.until(EC.presence_of_element_located((By.XPATH, '/html/body/div[1]/div/div[1]/label/textarea')))
        print("Found text area...")
        input_field.click()
        input_field.send_keys(seed_phrase)
        print("Entering seed phrase...")
        if debug_is_on:
            time.sleep(3)
            driver.save_screenshot("{}/08c_Enter_Seed_Phrase.png".format(screenshots_path))

        select_account_next = wait.until(EC.presence_of_element_located((By.XPATH, '/html/body/div[1]/div/div[2]/button')))
        select_account_next.click()
        print("Clicking continue button...")
        if debug_is_on:
            time.sleep(3)
            driver.save_screenshot("{}/08d_After_Seed_Phrase.png".format(screenshots_path))

        login = wait.until(EC.presence_of_element_located((By.XPATH, '/html/body/div[1]/div/button')))
        login.click()
        print("Clicking select account...")
        time.sleep(3)
        if debug_is_on:
            time.sleep(3)
            driver.save_screenshot("{}/08e_After_Selection_Accout.png".format(screenshots_path))

        storage = wait.until(EC.presence_of_element_located((By.XPATH, '//*[@id="root"]/div/div/div/div[4]/div[2]/h4')))
        storage.click()
        print("Selecting the 'storage' page...")
        time.sleep(3)
        if debug_is_on:
            time.sleep(3)
            driver.save_screenshot("{}/08f_After_Selecting_Storage.png".format(screenshots_path))

        print ("We appear to have correctly navigated to the storage page. Handing over to the Claim function :)")

    except TimeoutException:
        print("Failed to find or switch to the iframe within the timeout period.")
    except Exception as e:
        print(f"An error occurred: {e}")

def claim():
    if debug_is_on:
            print ("Looks like we're at the start of the Claim function")
            time.sleep(3)
            driver.save_screenshot("{}/09a_Start_of_Claim_function.png".format(screenshots_path))

    try:
        # Let's see how long until the wallet is ready to collect
        # As site lag with the HereWallet App changes, other WebDriverWait times might be more appropriate
        wait_time_dynamic = WebDriverWait(driver, 20)
        wait_time_xpath = '//*[@id="root"]/div/div[2]/div/div[3]/div/div[2]/div[1]/p[2]'
        wait_time_element = wait_time_dynamic.until(EC.visibility_of_element_located((By.XPATH, wait_time_xpath)))
        wait_time_text = wait_time_element.text
    except TimeoutException:
        print("Could not find the wait time element within the specified time.")
        wait_time_text = "Unknown"  # or set a default value or take another action as needed

    try:
        if debug_is_on:
            print (wait_time_text)
            time.sleep(3)
            driver.save_screenshot("{}/09b_After_Get_Wait_Time_function.png".format(screenshots_path))
        
        if wait_time_text == "Filled" or forceClaim:
            try:
                # First, try to click "Check NEWS" button if it exists
                wait_time_dynamic = WebDriverWait(driver, 30)
                print("Checking for news to read...")
                original_window = driver.current_window_handle
                check_news_button_xpath = '//button[contains(@class, "sc-ktwOSD") and contains(text(), "Check NEWS")]'
                check_news_button = wait_time_dynamic.until(EC.element_to_be_clickable((By.XPATH, check_news_button_xpath)))
                check_news_button.click()
                driver.switch_to.window(original_window)
                print("News checked. Waiting for claim button...")
                if debug_is_on:
                    driver.save_screenshot("{}/09c_after_checking_news_Seed.png".format(screenshots_path))
            except TimeoutException:
                print("No news to check or button not found.")

            try:
                # Now try to click "Claim HOT" button
                try:
                    # Let's double check if we have selected the iFrame after news
                    popup_body = WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.CLASS_NAME, "popup-body")))
                    iframe = popup_body.find_element(By.TAG_NAME, "iframe")
                    driver.switch_to.frame(iframe)

                except NoSuchElementException as e:
                    print(f"Iframe not found within popup_body: {e}")

                except Exception as e:
                    print(f"An unexpected error occurred while switching to iframe: {e}")

                wait_time_dynamic = WebDriverWait(driver, 60)
                
                print("Attempting to claim...")
                if debug_is_on:
                    time.sleep(3)
                    driver.save_screenshot("{}/9d_before_clicking_claim_HOT.png".format(screenshots_path))
                    page_source = driver.page_source
                    current_url = driver.current_url 
                    with open("debug_info.txt", "w") as f:
                        f.write("Page Source:\n")
                        f.write(page_source)
                        f.write("\n\nCurrent URL:\n")
                        f.write(current_url)
                    claim_button_xpath = "//button[contains(@class, 'sc-ktwOSD') and contains(text(), 'Claim HOT')]"
                    claim_button = WebDriverWait(driver, 10).until(EC.visibility_of_element_located((By.XPATH, claim_button_xpath)))
                    claim_button.click()

                if debug_is_on:
                    time.sleep(3)
                    driver.save_screenshot("{}/9e_after_clicking_claim_HOT.png".format(screenshots_path))

                print("Claim attempted. Please check the status.")
                # Now let's try again to get the time remaining until filled. 
                wait_time_dynamic = WebDriverWait(driver, 30)
                wait_time_xpath = '//*[@id="root"]/div/div[2]/div/div[3]/div/div[2]/div[1]/p[2]'
                wait_time_element = wait_time_dynamic.until(EC.visibility_of_element_located((By.XPATH, wait_time_xpath)))
                wait_time_text = wait_time_element.text

                time.sleep(5)
                if debug_is_on:
                    driver.save_screenshot("{}/9f_before_get_time_remaining.png".format(screenshots_path))
                # Extract time from wait_time_text
                matches = re.findall(r'(\d+)([hm])', wait_time_text)
                total_wait_time = sum(int(value) * (60 if unit == 'h' else 1) for value, unit in matches)
                print("Post claim raw wait time: %s & Processed = %s" % (wait_time_text, total_wait_time))
                if debug_is_on:
                    driver.save_screenshot("{}/9g_after_get_time_remaining.png".format(screenshots_path))
                return max(60, total_wait_time)  # Wait one hour unless it updated

            except TimeoutException:
                print("Unable to claim at this time. Will retry after one hour.")
                return 60
            except Exception as e:
                print(f"An error occurred while trying to claim: {e}")
                return 60

        else:
            # If the wallet isn't ready to be claimed, calculate wait time based on the timer provided on the page
            matches = re.findall(r'(\d+)([hm])', wait_time_text)
            if matches:
                total_time = sum(int(value) * (60 if unit == 'h' else 1) for value, unit in matches)
                print("Not Time to Claim seed yet. Wait for {} Minutes.".format(total_time))
                return max(5, total_time)  # Reduce 5 minutes as buffer
            else:
                print("No clear timer found. Check again later.")
                return 60  # Default wait time when no specific time is found
    except Exception as e:
        print("An unexpected error occurred: {}".format(e))
        return 60  # Default wait time in case of an unexpected error

# Define your base path for screenshots
screenshot_base = os.path.join(screenshots_path, "screenshot")

def clear_screen():
    # For Windows
    if os.name == 'nt':
        os.system('cls')
    # For macOS and Linux(here, os.name is 'posix')
    else:
        os.system('clear')

def validate_seed_phrase():
    """
    Prompts the user for a seed phrase, validates it, and returns the valid seed phrase.

    Returns:
        str: The valid seed phrase.

    Raises:
        ValueError: If the user fails to provide a valid seed phrase.
    """
    while True:
        seed_phrase = input("Please enter your 12-word seed phrase: ")
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
    global seed_phrase
    seed_phrase = validate_seed_phrase()
    clear_screen()
    print("Starting the login process...")
    log_into_telegram()
    next_steps()
    while True:
        wait_time = claim()
        global forceClaim
        forceClaim = False
        print(f"Need to wait for {wait_time} minutes before the next claim attempt.")

        while wait_time > 0:
            this_wait = min(wait_time, 15)
            print(f"Waiting for {this_wait} more minutes...")
            time.sleep(this_wait * 60)  # Convert minutes to seconds
            wait_time -= this_wait
            if wait_time > 0:
                print(f"Updated wait time: {wait_time} minutes left.")

if __name__ == "__main__":
    main()
