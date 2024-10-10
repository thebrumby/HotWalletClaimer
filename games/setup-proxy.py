import os
import re
import subprocess
import sys
import time

# Attempt to import httpx, install if necessary
try:
    import httpx
except ImportError:
    print("httpx is not installed. Installing now...")
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "httpx"])
        import httpx
    except Exception as e:
        print(f"Failed to install httpx: {e}")
        sys.exit(1)

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
    proxy_pattern = re.compile(
        r'--mode upstream:(http[s]?)://(.*?):(\d+)(?:\s+--upstream-auth\s+(\S+):(\S+))?',
        re.DOTALL
    )
    match = proxy_pattern.search(script_content)
    if match:
        scheme, host, port, username, password = match.groups()
        return {
            "scheme": scheme,
            "host": host,
            "port": port,
            "username": username,
            "password": password
        }
    return None

def prompt_user_for_proxy_details():
    host = input("Enter upstream proxy host (IP or URL): ").strip()
    port = input("Enter upstream proxy port: ").strip()
    username = input("Enter upstream proxy username (leave blank if not required): ").strip()
    password = input("Enter upstream proxy password (leave blank if not required): ").strip()

    if not (host and port):
        print("Host and port are required.")
        return None

    return host, port, username or None, password or None

def prompt_insecure_credential_validation():
    allow_insecure = input("Allow insecure VPN credential validation (y/N): ").strip().lower()
    if allow_insecure == 'y':
        confirm = input("This will allow your credentials to be viewed by others and should only be done as a last resort - continue (y/N): ").strip().lower()
        return confirm == 'y'
    return False

def test_proxy_connection(host, port, username, password, use_https):
    scheme = "https" if use_https else "http"
    if username and password:
        proxy_url = f"{scheme}://{username}:{password}@{host}:{port}"
    else:
        proxy_url = f"{scheme}://{host}:{port}"
    test_url = 'https://web.telegram.org'
    test_proxy_anonymity(proxy_url)
    expected_word_count = 3
    print(f"Testing the proxy credentials with {scheme.upper()}...")

    proxies = {
        'http://': proxy_url,
        'https://': proxy_url,
    }

    try:
        with httpx.Client(proxies=proxies, timeout=10) as client:
            result = client.get(test_url, follow_redirects=False)
            if result.status_code == 200:
                telegram_count = result.text.count("Telegram")
                if telegram_count > expected_word_count:
                    print("Proxy connection successful.")
                    print(f"Response: 200, Telegram word count: {telegram_count}")
                    return True
                else:
                    print(f"Proxy connection failed: Unexpected content. 'Telegram' count is {telegram_count}.")
                    return False
            else:
                print(f"Proxy connection failed with status code: {result.status_code}")
                return False
    except httpx.RequestError as e:
        print(f"Proxy connection failed: {e}")
        return False

def update_start_script(host, port, username, password, use_https):
    scheme = "https" if use_https else "http"
    upstream_auth = f" --upstream-auth {username}:{password}" if username and password else ""
    start_script_content = f"""#!/bin/bash
./venv/bin/mitmdump --mode upstream:{scheme}://{host}:{port}{upstream_auth} -s {os.path.join(PROXY_DIR, 'modify_requests_responses.py')} > /dev/null 2>&1
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

def test_proxy_anonymity(proxy_url):
    test_url = 'https://httpbin.org/get'
    try:
        # First, get the client's real IP address by making a direct request
        real_ip = None
        try:
            with httpx.Client(timeout=10) as client:
                response = client.get(test_url)
                data = response.json()
                real_ip = data.get('origin', '')
        except Exception as e:
            print(f"Failed to get real IP address: {e}")
            return None

        # Now, make a request through the proxy
        proxies = {
            'http://': proxy_url,
            'https://': proxy_url,
        }
        with httpx.Client(proxies=proxies, timeout=10) as client:
            response = client.get(test_url)
            data = response.json()
            headers = data.get('headers', {})
            origin = data.get('origin', '')

            # Check for anonymity
            if origin == real_ip:
                print("Proxy is Transparent (NOA)")
                print("Explanation: The proxy passes your real IP address to the server. Your IP is exposed.")
                return 'NOA'
            elif 'X-Forwarded-For' in headers or 'Via' in headers:
                print("Proxy is Anonymous (ANM)")
                print("Explanation: The proxy hides your IP address but reveals that you're using a proxy.")
                return 'ANM'
            else:
                print("Proxy is Elite (HIA)")
                print("Explanation: The proxy hides your IP address and does not disclose proxy usage.")
                return 'HIA'
    except Exception as e:
        print(f"Failed to test proxy anonymity: {e}")
        return None

def main():
    script_content = read_start_script()
    if script_content is None:
        return

    print("For testing purposes, you can obtain a free account with limited data at https://www.webshare.io/features/free-proxy")

    upstream_proxy = check_upstream_proxy(script_content)
    if upstream_proxy:
        print("Current upstream proxy configuration:")
        print(f"Scheme: {upstream_proxy['scheme']}")
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
            update_start_script("", "", "", "", True)  # Remove upstream configuration
            subprocess.run(['pm2', 'save'], check=True)  # Save the PM2 state after removing the configuration
            unlock_file()
            print("Upstream proxy removed.")
            return

    while True:
        proxy_details = prompt_user_for_proxy_details()
        if proxy_details:
            host, port, username, password = proxy_details
            use_https = not prompt_insecure_credential_validation()
            if test_proxy_connection(host, port, username, password, use_https):
                lock_file()
                stop_and_delete_pm2_process()
                update_start_script(host, port, username, password, use_https)
                restart_proxy()
                unlock_file()
                break
            else:
                print("Proxy test failed. Please re-enter the proxy details.")
        else:
            print("Invalid input. Please provide all the necessary details.")

if __name__ == "__main__":
    main()