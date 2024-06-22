import os
import subprocess
import shutil
import time

PROXY_DIR = os.path.abspath("./proxy")
USER_REQUESTED_IP_FILE = os.path.join(PROXY_DIR, 'user_requested_outgoing_ip.txt')
SQUID_WORKING_IP_FILE = os.path.join(PROXY_DIR, 'squid_working_outgoing_ip.txt')

log_to_file = False  # Set this to False to log to /dev/null

def get_log_file_path():
    return os.path.join(PROXY_DIR, 'mitmproxy.log') if log_to_file else '/dev/null'

def check_pm2_process_exists(process_name):
    try:
        result = subprocess.run(['pm2', 'list'], capture_output=True, text=True)
        return process_name in result.stdout
    except Exception as e:
        print(f"An error occurred while checking PM2 process: {e}")
        return False

def install_mitmproxy():
    subprocess.run(['pip3', 'install', 'mitmproxy'], check=True)

def install_squid():
    try:
        subprocess.run(['apt-get', 'update'], check=True)
        subprocess.run(['apt-get', 'install', '-y', 'squid'], check=True)
    except Exception as e:
        print(f"An error occurred while installing Squid: {e}")

def copy_certificates():
    mitmproxy_cert_path = os.path.expanduser('~/.mitmproxy/mitmproxy-ca-cert.pem')
    if os.path.exists(mitmproxy_cert_path):
        sudo_password = os.getenv('SUDO_PASSWORD')
        if shutil.which('sudo'):
            command1 = f'echo {sudo_password} | sudo -S cp {mitmproxy_cert_path} /usr/local/share/ca-certificates/mitmproxy-ca-cert.crt'
            command2 = f'echo {sudo_password} | sudo -S update-ca-certificates'
        else:
            command1 = f'cp {mitmproxy_cert_path} /usr/local/share/ca-certificates/mitmproxy-ca-cert.crt'
            command2 = 'update-ca-certificates'
        subprocess.run(command1, shell=True, check=True)
        subprocess.run(command2, shell=True, check=True)
    else:
        print(f"Certificate not found at {mitmproxy_cert_path}")

def write_modify_requests_responses_script():
    script_content = """
from mitmproxy import http

def request(flow: http.HTTPFlow) -> None:
    # Log the original User-Agent header
    original_user_agent = flow.request.headers.get('User-Agent', 'No User-Agent header')
    print(f"Original User-Agent: {original_user_agent}")
    
    # Check if the response object is not None before accessing its headers
    if flow.response and ('cf-cache-status' in flow.response.headers or 'cloudflare' in flow.response.headers.get('server', '').lower()):
        # Modify User-Agent header
        flow.request.headers['User-Agent'] = 'Mozilla/5.0 (iPhone; CPU iPhone OS 17_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) EdgiOS/124.0.2478.50 Version/17.0 Mobile/15E148 Safari/604.1'
        print("Modified User-Agent for Cloudflare-protected site")
    else:
        print("Request not modified for Cloudflare-protected site")

    # Log the modified headers
    print(f"Modified Request Headers: {flow.request.headers}")

def response(flow: http.HTTPFlow) -> None:
    # Remove headers
    if 'Content-Security-Policy' in flow.response.headers:
        del flow.response.headers['Content-Security-Policy']
    if 'X-Frame-Options' in flow.response.headers:
        del flow.response.headers['X-Frame-Options']

    # Modify script to replace tgWebAppPlatform
    if flow.response.content:
        content = flow.response.content.decode('utf-8')
        content = content.replace('tgWebAppPlatform=weba', 'tgWebAppPlatform=iOS')
        content = content.replace('tgWebAppPlatform=web', 'tgWebAppPlatform=iOS')
        flow.response.content = content.encode('utf-8')

    # Log the modified response headers
    print(f"Modified Response Headers: {flow.response.headers}")
"""
    os.makedirs(PROXY_DIR, exist_ok=True)
    with open(os.path.join(PROXY_DIR, 'modify_requests_responses.py'), 'w') as file:
        file.write(script_content)

def write_start_script():
    start_script_content = f"""#!/bin/bash
./venv/bin/mitmdump --mode upstream:http://localhost:3128 -s {os.path.join(PROXY_DIR, 'modify_requests_responses.py')} > {get_log_file_path()} 2>&1
"""
    os.makedirs(PROXY_DIR, exist_ok=True)
    with open(os.path.join(PROXY_DIR, 'start_mitmproxy.sh'), 'w') as file:
        file.write(start_script_content)
    os.chmod(os.path.join(PROXY_DIR, 'start_mitmproxy.sh'), 0o755)

def write_squid_config(outgoing_ip):
    squid_config_content = f"""
http_port 3128

# Define an ACL for localhost
acl localnet src 127.0.0.1/32 ::1

# Only allow requests from localhost
http_access allow localnet
http_access deny all

# Define the outgoing address
tcp_outgoing_address {outgoing_ip} localnet
"""
    os.makedirs('/etc/squid', exist_ok=True)
    with open('/etc/squid/squid.conf', 'w') as file:
        file.write(squid_config_content)

def get_outgoing_ip():
    os.makedirs(PROXY_DIR, exist_ok=True)
    if os.path.exists(USER_REQUESTED_IP_FILE):
        with open(USER_REQUESTED_IP_FILE, 'r') as file:
            return file.read().strip()
    else:
        # Write the current server IP to the file
        current_ip = subprocess.check_output(['hostname', '-I']).decode().strip().split()[0]
        with open(USER_REQUESTED_IP_FILE, 'w') as file:
            file.write(current_ip)
        return current_ip

def update_working_ip(ip):
    with open(SQUID_WORKING_IP_FILE, 'w') as file:
        file.write(ip)

def restart_squid():
    subprocess.run(['squid', '-k', 'reconfigure'], check=True)

def start_pm2_app(script_path, app_name):
    command = f"NODE_NO_WARNINGS=1 pm2 start {script_path} --name {app_name} --interpreter bash --watch {script_path} --output /dev/null --error /dev/null --log-date-format 'YYYY-MM-DD HH:mm Z'"
    subprocess.run(command, shell=True, check=True)

def main():
    process_name = "http-proxy"

    # Check if IP files exist and read their values
    user_ip = get_outgoing_ip()
    if os.path.exists(SQUID_WORKING_IP_FILE):
        with open(SQUID_WORKING_IP_FILE, 'r') as file:
            working_ip = file.read().strip()
    else:
        working_ip = None

    # Check if the PM2 process exists
    pm2_process_exists = check_pm2_process_exists(process_name)

    # If the user requested IP and working IP differ, or if the PM2 process doesn't exist, proceed with setup
    if user_ip != working_ip or not pm2_process_exists:
        if user_ip != working_ip:
            print(f"User requested IP {user_ip} differs from working IP {working_ip}. Updating Squid configuration.")
            write_squid_config(user_ip)
            restart_squid()
            update_working_ip(user_ip)
        if not pm2_process_exists:
            print("Installing mitmproxy...")
            install_mitmproxy()

            print("Installing Squid...")
            install_squid()

            print("Copying certificates...")
            copy_certificates()

            print("Writing modify_requests_responses.py...")
            write_modify_requests_responses_script()

            print("Writing start_mitmproxy.sh...")
            write_start_script()

            print("Writing Squid configuration...")
            write_squid_config(user_ip)

            print("Restarting Squid service...")
            restart_squid()

            print("Creating PM2 process...")
            start_pm2_app(os.path.join(PROXY_DIR, 'start_mitmproxy.sh'), 'http-proxy')

            print("Saving PM2 process list...")
            subprocess.run(['pm2', 'save'], check=True)

            update_working_ip(user_ip)
            print("Setup complete. The http-proxy process is now running.")

            # Pause for 10 seconds before finishing
            time.sleep(10)

    else:
        print("The user requested IP matches the working IP and the PM2 process is running. Skipping setup.")

if __name__ == "__main__":
    main()