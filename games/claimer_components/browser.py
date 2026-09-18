"""Chrome lifecycle, user agents, cookies and proxy startup."""

import os
import shutil
import time
import json
import subprocess
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options


class BrowserMixin:
    """Chrome lifecycle, user agents, cookies and proxy startup. Uses the shared state on Claimer."""

    def prompt_user_agent(self):
        print (f"Step {self.step} - Please enter the User-Agent string you wish to use or press enter for default.")
        user_agent = input(f"Step {self.step} - User-Agent: ").strip()
        return user_agent

    def set_cookies(self):
        if not (self.forceRequestUserAgent or self.settings["requestUserAgent"]):
            cookies_path = f"{self.session_path}/cookies.json"
            cookies = self.driver.get_cookies()
            with open(cookies_path, 'w') as file:
                json.dump(cookies, file)
        else:
            user_agent = self.prompt_user_agent()
            cookies_path = f"{self.session_path}/cookies.json"
            cookies = self.driver.get_cookies()
            cookies.append({"name": "user_agent", "value": user_agent})  # Save user agent to cookies
            with open(cookies_path, 'w') as file:
                json.dump(cookies, file)

    def setup_driver(self):
        chrome_options = Options()
        chrome_options.add_argument(f"user-data-dir={self.session_path}")
        chrome_options.add_argument("--profile-directory=Default")
        chrome_options.add_argument("--headless=new")  # Ensure headless is enabled
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--enable-features=NetworkService,NetworkServiceInProcess")
        chrome_options.add_argument("--disable-background-networking")
        chrome_options.add_argument("--enable-automation")

        # Attempt to load user agent from cookies
        try:
            cookies_path = f"{self.session_path}/cookies.json"
            with open(cookies_path, 'r') as file:
                cookies = json.load(file)
                user_agent_cookie = next((cookie for cookie in cookies if cookie["name"] == "user_agent"), None)
                if user_agent_cookie and user_agent_cookie["value"]:
                    user_agent = user_agent_cookie["value"]
                    self.output(f"Using saved user agent: {user_agent}", 2)
                else:
                    user_agent = "Mozilla/5.0 (iPhone; CPU iPhone OS 17_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) EdgiOS/124.0.2478.50 Version/17.0 Mobile/15E148 Safari/604.1"
                    self.output("No user agent found, using default.", 2)
        except FileNotFoundError:
            user_agent = "Mozilla/5.0 (iPhone; CPU iPhone OS 17_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) EdgiOS/124.0.2478.50 Version/17.0 Mobile/15E148 Safari/604.1"
            self.output("Cookies file not found, using default user agent.", 2)

        # Adjust the platform based on the user agent
        if any(keyword in user_agent for keyword in ['iPhone', 'iPad', 'iOS', 'iPhone OS']):
            self.default_platform = "ios"
            self.output("Detected iOS platform from user agent. tgWebAppPlatform will be changed to 'ios' later.", 2)
        elif 'Android' in user_agent:
            self.default_platform = "android"
            self.output("Detected Android platform from user agent. Set tgWebAppPlatform to 'android'.", 2)
        else:
            self.default_platform = "web"
            self.output("Default platform set to 'web'.", 3)

        chrome_options.add_argument(f"user-agent={user_agent}")
        chrome_options.add_argument("--disable-blink-features=AutomationControlled")
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option('useAutomationExtension', False)

        if not self.settings.get("enableCache", True) and int(self.step) >= 100:
            chrome_options.add_argument("--disable-application-cache")

        if self.settings["useProxy"] or self.forceLocalProxy:
            proxy_server = self.settings["proxyAddress"]
            chrome_options.add_argument(f"--proxy-server={proxy_server}")

        chrome_options.add_argument("--ignore-certificate-errors")
        chrome_options.add_argument("--allow-running-insecure-content")
        chrome_options.add_argument("--test-type")

        chromedriver_path = shutil.which("chromedriver")
        if chromedriver_path is None:
            self.output("ChromeDriver not found in PATH. Please ensure it is installed.", 1)
            exit(1)

        try:
            service = Service(chromedriver_path)
            self.driver = webdriver.Chrome(service=service, options=chrome_options)
            return self.driver
        except Exception as e:
            self.output(f"Initial ChromeDriver setup may have failed: {e}", 1)
            self.output("Please ensure you have the correct ChromeDriver version for your system.", 1)
            exit(1)

    def run_http_proxy(self):
        proxy_lock_file = "./start_proxy.txt"
        max_wait_time = 15 * 60  # 15 minutes
        wait_interval = 5  # 5 seconds
        start_time = time.time()
        message_displayed = False

        while os.path.exists(proxy_lock_file) and (time.time() - start_time) < max_wait_time:
            if not message_displayed:
                self.output("Proxy is already running. Waiting for it to free up...", 2)
                message_displayed = True
            time.sleep(wait_interval)

        if os.path.exists(proxy_lock_file):
            self.output("Max wait time elapsed. Proceeding to run the proxy.", 2)

        with open(proxy_lock_file, "w") as lock_file:
            lock_file.write(f"Proxy started at: {time.ctime()}\n")

        try:
            subprocess.run(['./launch.sh', 'enable-proxy'], check=True)
            self.output("http-proxy started successfully.", 2)
        except subprocess.CalledProcessError as e:
            self.output(f"Failed to start http-proxy: {e}", 1)
        finally:
            os.remove(proxy_lock_file)

    def get_driver(self):
        if self.driver is None:  # Check if driver needs to be initialized
            self.manage_session()  # Ensure we can start a session
            self.driver = self.setup_driver()
            self.output("\nCHROME DRIVER INITIALISED: Try not to exit the script before it detaches.",2)
        return self.driver

    def quit_driver(self):
        if self.driver:
            self.driver.quit()
            self.output("\nCHROME DRIVER DETACHED: It is now safe to exit the script.",2)
            self.driver = None
            self.release_session()  # Mark the session as closed
