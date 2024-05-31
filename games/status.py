import subprocess
from datetime import datetime, timedelta

def run_command(command):
    """ Helper function to run a shell command and return its output """
    return subprocess.run(command, text=True, shell=True, capture_output=True).stdout

def parse_time_from_log(line):
    """ Extract and parse time from log line, format it to '31 May - 17:45' """
    time_str = line.split("Need to wait until ")[1].split(' ')[0]
    if ':' in time_str:  # Ensure it's a time string
        now = datetime.now()
        claim_time = datetime.strptime(time_str, "%H:%M")
        claim_time = datetime(now.year, now.month, now.day, claim_time.hour, claim_time.minute)
        if claim_time < now:  # Adjust for claims that cross midnight
            claim_time += timedelta(days=1)
        return claim_time.strftime("%d %B - %H:%M")
    return None

def fetch_and_process_logs(process_name, status):
    """ Fetch logs, extract details, and print them """
    sanitized_process_name = process_name.replace(':', '-')
    log_file = f"/root/.pm2/logs/{sanitized_process_name}-out.log"
    logs = run_command(f"tail -n 50 {log_file}")

    # Extract details from logs
    balance = None
    wait_time = None
    log_status = None

    for line in reversed(logs.splitlines()):
        if balance is None and "After Balance after claiming:" in line:
            balance = line.split("After Balance after claiming: ")[1].strip()
        if wait_time is None and "Need to wait until" in line:
            wait_time = parse_time_from_log(line)
        if log_status is None and line.startswith("Step"):
            log_status = line.split("- ", 1)[1]

    print(f"{process_name} | Balance: {balance} | Next claim at: {wait_time} | Status: {log_status}")

def main():
    # Fetch stopped processes
    stopped_processes = run_command("pm2 list | grep stopped | awk '{print $4}'")
    print("Stopped Wallet Processes:")
    print("---------------------------------------")
    for process_name in stopped_processes.splitlines():
        if process_name:  # Check for empty lines
            fetch_and_process_logs(process_name, "stopped")

    # Fetch running processes
    running_processes = run_command("pm2 list | grep online | awk '{print $4}'")
    print("---------------------------------------")
    print("Running Wallet Processes:")
    print("---------------------------------------")
    for process_name in running_processes.splitlines():
        if process_name:  # Check for empty lines
            fetch_and_process_logs(process_name, "online")

if __name__ == "__main__":
    main()