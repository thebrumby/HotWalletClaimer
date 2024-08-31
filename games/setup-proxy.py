import os
import re
import subprocess
import time
import requests

PROXY_DIR = os.path.abspath("./proxy")
START_SCRIPT_PATH = os.path.join(PROXY_DIR, 'start_mitmproxy.sh')
PROXY_LOCK_FILE = "./start_proxy.txt"
PM2_PROCESS_NAME = "http-proxy"

def read_start_script():
    if not os.path.exists(START_SCRIPT_PATH):
        print(f"{START_SCRIPT_PATH} does not exist.")
        return None
    
    with open(START_SCRIPT_PATH, 'r') as file:
        return file.read()

def check_upstream_proxy(script_content):
    proxy_pattern = re.compile(r'--mode upstream:https://(.*?):(\d+)\s+--upstream-auth\s+(\S+):(\S+)', re.DOTALL)
    match = proxy_pattern.search(script_content)
    if match:
        host, port, username, password = match.groups()
        return {
            "host": host,
            "port": port,
            "username": username,
            "password": password
        }
    return None

def prompt_user_for_proxy_details():
    host = input("Enter upstream proxy host (IP or URL): ").strip()
    port = input("Enter upstream proxy port: ").strip()
    username = input("Enter upstream proxy username: ").strip()
    password = input("Enter upstream proxy password: ").strip()

    if not (host and port and username and password):
        print("All fields are required.")
        return None

    return host, port, username, password

def test_proxy_connection(host, port, username, password):
    proxy = f"http://{username}:{password}@{host}:{port}"
    test_url = 'https://web.telegram.org'
    expected_word_count = 3
    print("Testing the proxy credentials...")

    # Clear proxy-related environment variables
    env = os.environ.copy()
    env.pop('HTTP_PROXY', None)
    env.pop('HTTPS_PROXY', None)
    env.pop('http_proxy', None)
    env.pop('https_proxy', None)

    try:
        result = requests.get(
            test_url,
            proxies={'http': proxy, 'https': proxy},
            timeout=10,
            allow_redirects=False  # Disable redirects to prevent potential fallback to non-proxy routes
        )

        # Ensure the request was successful and made through the proxy
        if result.status_code == 200:
            telegram_count = result.text.count("Telegram")
            if telegram_count > expected_word_count:
                print("Proxy connection successful.")
                print(f"Response: 200, Telegram word count: {telegram_count}")
                return True
            else:
                print(f"Proxy connection failed: Doesn't appear to be TG site. 'Telegram' count is {telegram_count}.")
                return False
        else:
            print(f"Proxy connection failed with status code: {result.status_code}")
            return False

    except requests.RequestException as e:
        print(f"Proxy connection failed: {e}")
        return False

def update_start_script(host, port, username, password):
    start_script_content = f"""#!/bin/bash
./venv/bin/mitmdump --mode upstream:https://{host}:{port} --upstream-auth {username}:{password} -s {os.path.join(PROXY_DIR, 'modify_requests_responses.py')} > /dev/null 2>&1
"""
    with open(START_SCRIPT_PATH, 'w') as file:
        file.write(start_script_content)
    os.chmod(START_SCRIPT_PATH, 0o755)

def stop_and_delete_pm2_process():
    try:
        subprocess.run(['pm2', 'stop', PM2_PROCESS_NAME], check=True)
        subprocess.run(['pm2', 'delete', PM2_PROCESS_NAME], check=True)
        subprocess.run(['pm2', 'save'], check=True)  # Save the PM2 state after deleting the process
    except subprocess.CalledProcessError as e:
        print(f"Error stopping/deleting PM2 process: {e}")

def lock_file():
    with open(PROXY_LOCK_FILE, "w") as lock_file:
        lock_file.write(f"Proxy setup in progress: {time.ctime()}\n")

def unlock_file():
    if os.path.exists(PROXY_LOCK_FILE):
        os.remove(PROXY_LOCK_FILE)

def restart_proxy():
    try:
        subprocess.run(['pm2', 'start', START_SCRIPT_PATH, '--name', PM2_PROCESS_NAME], check=True)
        subprocess.run(['pm2', 'save'], check=True)
        print("http-proxy restarted successfully.")
    except subprocess.CalledProcessError as e:
        print(f"Failed to restart http-proxy: {e}")

def main():
    script_content = read_start_script()
    if script_content is None:
        return

    upstream_proxy = check_upstream_proxy(script_content)
    if upstream_proxy:
        print("Current upstream proxy configuration:")
        print(f"Host: {upstream_proxy['host']}")
        print(f"Port: {upstream_proxy['port']}")
        print(f"Username: {upstream_proxy['username']}")
        print(f"Password: {upstream_proxy['password']}")
    else:
        print("No upstream proxy configuration is currently set.")

    if upstream_proxy:
        choice = input("An upstream proxy is already configured. Enter 'y' to remove it, or press Enter to enter new credentials: ").strip().lower()
        if choice == 'y':
            lock_file()
            stop_and_delete_pm2_process()
            update_start_script("", "", "", "")  # Remove upstream configuration
            subprocess.run(['pm2', 'save'], check=True)  # Save the PM2 state after removing the configuration
            unlock_file()
            print("Upstream proxy removed.")
            return

    while True:
        proxy_details = prompt_user_for_proxy_details()
        if proxy_details:
            host, port, username, password = proxy_details
            if test_proxy_connection(host, port, username, password):
                lock_file()
                stop_and_delete_pm2_process()
                update_start_script(host, port, username, password)
                restart_proxy()
                unlock_file()
                break
            else:
                print("Proxy test failed. Please re-enter the proxy details.")
        else:
            print("Invalid input. Please provide all the necessary details.")

if __name__ == "__main__":
    main()