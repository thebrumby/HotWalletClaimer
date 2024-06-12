import os
import subprocess
import shutil

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
        command1 = f'echo {sudo_password} | sudo -S cp {mitmproxy_cert_path} /usr/local/share/ca-certificates/mitmproxy-ca-cert.crt'
        command2 = f'echo {sudo_password} | sudo -S update-ca-certificates'
        subprocess.run(command1, shell=True, check=True)
        subprocess.run(command2, shell=True, check=True)
    else:
        print(f"Certificate not found at {mitmproxy_cert_path}")

def write_remove_headers_script():
    script_content = """
from mitmproxy import http

def response(flow: http.HTTPFlow) -> None:
    if 'Content-Security-Policy' in flow.response.headers:
        del flow.response.headers['Content-Security-Policy']
    if 'X-Frame-Options' in flow.response.headers:
        del flow.response.headers['X-Frame-Options']
"""
    with open('remove_headers.py', 'w') as file:
        file.write(script_content)

def write_start_script():
    start_script_content = """#!/bin/bash
./venv/bin/mitmdump -s remove_headers.py
"""
    with open('start_mitmproxy.sh', 'w') as file:
        file.write(start_script_content)
    os.chmod('start_mitmproxy.sh', 0o755)

def start_pm2_app(script_path, app_name):
    command = f"NODE_NO_WARNINGS=1 pm2 start {script_path} --name {app_name} --interpreter bash --watch {script_path}"
    subprocess.run(command, shell=True, check=True)

def main():
    process_name = "http-proxy"

    if check_pm2_process_exists(process_name):
        print(f"The PM2 process '{process_name}' already exists. Exiting...")
        return

    print("Installing mitmproxy...")
    install_mitmproxy()

    print("Copying certificates...")
    copy_certificates()

    print("Writing remove_headers.py...")
    write_remove_headers_script()

    print("Writing start_mitmproxy.sh...")
    write_start_script()

    print("Creating PM2 process...")
    start_pm2_app('start_mitmproxy.sh', 'http-proxy')

    print("Saving PM2 process list...")
    subprocess.run(['pm2', 'save'], check=True)

    print("Setup complete. The http-proxy process is now running.")

if __name__ == "__main__":
    main()