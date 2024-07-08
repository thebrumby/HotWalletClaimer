# Start a new PM2 process
import subprocess
import sys

def start_pm2_app(script_path, app_name, session_name):
    interpreter_path = "venv/bin/python3"
    command = (
        f"NODE_NO_WARNINGS=1 pm2 start {script_path} "
        f"--name {app_name} "
        f"--interpreter {interpreter_path} "
        f"--watch {script_path} "
        f"--output /dev/null "  # Redirect stdout to /dev/null
        f"--error {app_name}_error.log "  # Log stderr to a specific file
        f"-- {session_name}"
    )
    subprocess.run(command, shell=True, check=True)

def save_pm2():
    command = "NODE_NO_WARNINGS=1 pm2 save"
    result = subprocess.run(command, shell=True, text=True, capture_output=True)
    print(result.stdout)
