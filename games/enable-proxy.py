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

def install_wheel_if_missing():
    try:
        __import__('wheel')
    except ImportError:
        print("Installing missing wheel package...")
        subprocess.run(['pip3', 'install', 'wheel'], check=True)

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
from mitmproxy import http, ctx
import re
import zlib
import brotli

def load(l):
    ctx.log.info("modify_requests_responses.py script has started.")

# Modify outgoing requests (client to server)
def request(flow: http.HTTPFlow) -> None:
    try:
        if flow.request:
            # Replace 'tgWebAppPlatform=web' with 'tgWebAppPlatform=ios' in all URLs
            if "tgWebAppPlatform=web" in flow.request.url:
                ctx.log.info(f"Modifying outgoing URL: {flow.request.url}")
                flow.request.url = flow.request.url.replace("tgWebAppPlatform=web", "tgWebAppPlatform=ios")
                ctx.log.info(f"Modified outgoing URL to: {flow.request.url}")
                
            # Detect platform via User-Agent and redirect 'telegram-web-app.js'
            user_agent = flow.request.headers.get('User-Agent', '')
            if 'telegram-web-app.js' in flow.request.pretty_url:
                if any(keyword in user_agent for keyword in ['iPhone', 'iPad', 'iOS', 'iPhone OS']):
                    # Redirect for iOS
                    flow.request.path = flow.request.path.replace('telegram-web-app.js', 'games/utils/ios-60-telegram-web-app.js')
                    ctx.log.info("Redirected to iOS-specific JavaScript for iOS platform.")
                elif 'Android' in user_agent:
                    # Redirect for Android
                    flow.request.path = flow.request.path.replace('telegram-web-app.js', 'games/utils/android-60-telegram-web-app.js')
                    ctx.log.info("Redirected to Android-specific JavaScript for Android platform.")
    except Exception as e:
        ctx.log.error(f"Error modifying outgoing request for URL {flow.request.url}: {e}")

# Modify incoming responses (server to client)
def response(flow: http.HTTPFlow) -> None:
    try:
        # Remove specific headers
        headers_to_remove = ['Content-Security-Policy', 'X-Frame-Options']
        removed_headers = []
        for header in headers_to_remove:
            if header in flow.response.headers:
                del flow.response.headers[header]
                removed_headers.append(header)

        if removed_headers:
            ctx.log.info(f"Removed headers from URL: {flow.request.url}")
            ctx.log.debug(f"Removed Headers: {removed_headers}")

        # Modify content if necessary
        content_type = flow.response.headers.get("content-type", "").lower()
        content_encoding = flow.response.headers.get("content-encoding", "").lower()

        # Check if content is of type HTML, JavaScript, or JSON
        if any(ct in content_type for ct in ["text/html", "application/javascript", "application/json", "text/javascript"]):
            # Decompress if content is compressed
            if "gzip" in content_encoding:
                decoded_content = zlib.decompress(flow.response.content, zlib.MAX_WBITS | 16).decode('utf-8', errors='replace')
                compressed = 'gzip'
            elif "br" in content_encoding:
                decoded_content = brotli.decompress(flow.response.content).decode('utf-8', errors='replace')
                compressed = 'br'
            else:
                decoded_content = flow.response.text
                compressed = None

            # Replace 'tgWebAppPlatform=web' with 'tgWebAppPlatform=ios' in content
            if "tgWebAppPlatform=web" in decoded_content:
                ctx.log.info(f"'tgWebAppPlatform=web' found in response for URL: {flow.request.url}")
                modified_content = decoded_content.replace("tgWebAppPlatform=web", "tgWebAppPlatform=ios")

                # Re-encode and compress if necessary
                if compressed == 'gzip':
                    flow.response.content = zlib.compress(modified_content.encode('utf-8'))
                    ctx.log.info("Content recompressed with gzip.")
                elif compressed == 'br':
                    flow.response.content = brotli.compress(modified_content.encode('utf-8'))
                    ctx.log.info("Content recompressed with Brotli.")
                else:
                    flow.response.text = modified_content

                ctx.log.info(f"Modified content in response for URL: {flow.request.url}")

            # Update content length if necessary
            if 'content-length' in flow.response.headers:
                flow.response.headers['content-length'] = str(len(flow.response.content))

    except Exception as e:
        ctx.log.error(f"Error processing response for URL {flow.request.url}: {e}")
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
        install_wheel_if_missing()

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