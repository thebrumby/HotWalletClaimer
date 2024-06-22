import os
import subprocess
import shutil
import time

PROXY_DIR = os.path.abspath("./proxy")

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
./venv/bin/mitmdump -s {os.path.join(PROXY_DIR, 'modify_requests_responses.py')} > {get_log_file_path()} 2>&1
"""
    os.makedirs(PROXY_DIR, exist_ok=True)
    with open(os.path.join(PROXY_DIR, 'start_mitmproxy.sh'), 'w') as file:
        file.write(start_script_content)
    os.chmod(os.path.join(PROXY_DIR, 'start_mitmproxy.sh'), 0o755)

def start_pm2_app(script_path, app_name):
    command = f"NODE_NO_WARNINGS=1 pm2 start {script_path} --name {app_name} --interpreter bash --watch {script_path} --output /dev/null --error /dev/null --log-date-format 'YYYY-MM-DD HH:mm Z'"
    subprocess.run(command, shell=True, check=True)

def main():
    process_name = "http-proxy"

    # Check if the PM2 process exists
    pm2_process_exists = check_pm2_process_exists(process_name)

    # If the PM2 process doesn't exist, proceed with setup
    if not pm2_process_exists:
        print("Installing mitmproxy...")
        install_mitmproxy()

        print("Copying certificates...")
        copy_certificates()

        print("Writing modify_requests_responses.py...")
        write_modify_requests_responses_script()

        print("Writing start_mitmproxy.sh...")
        write_start_script()

        print("Creating PM2 process...")
        start_pm2_app(os.path.join(PROXY_DIR, 'start_mitmproxy.sh'), 'http-proxy')

        print("Saving PM2 process list...")
        subprocess.run(['pm2', 'save'], check=True)

        print("Setup complete. The http-proxy process is now running.")

        time.sleep(5)

    else:
        print("The PM2 process is running. Skipping setup.")

if __name__ == "__main__":
    main()