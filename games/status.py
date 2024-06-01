import subprocess
from datetime import datetime

def run_command(command):
    """ Run a shell command and return its output """
    return subprocess.run(command, text=True, shell=True, capture_output=True).stdout

def parse_time_from_log(line):
    try:
        time_str = line.split("Need to wait until ")[1].split(' before')[0]
        try:
            parsed_time = datetime.strptime(time_str, "%d %B - %H:%M")
        except ValueError:
            parsed_time = datetime.strptime(time_str, "%H:%M")
        return parsed_time.strftime("%d %B - %H:%M")
    except Exception as e:
        print(f"Failed to parse time from line: {line}. Error: {e}")
        return "None"

def truncate_and_pad(string, length):
    """ Truncate and pad a string to a specified length """
    if string is None:
        string = "None"
    if len(string) > length:
        return (string[:length-3] + '...').ljust(length)
    else:
        return string.ljust(length)

def extract_balance(line):
    """ Extract balance from a log line """
    if "BALANCE:" in line:
        return line.split("BALANCE:")[1].strip()
    return "None"

def extract_status(line):
    """ Extract status from a log line """
    if "STATUS:" in line:
        return line.split("STATUS:")[1].strip()
    return "None"

def fetch_and_process_logs(process_name, status):
    """ Fetch logs, extract details, and print them """
    sanitized_process_name = process_name.replace(':', '-')
    log_file = f"/root/.pm2/logs/{sanitized_process_name}-out.log"
    logs = run_command(f"tail -n 200 {log_file}")  # Increased the number of lines to ensure more comprehensive data capture

    balance = "None"
    next_claim_at = "None"
    log_status = "None"

    relevant_lines = [line for line in reversed(logs.splitlines()) if "BALANCE:" in line or "STATUS:" in line or "Need to wait until" in line]

    for line in relevant_lines:
        if "BALANCE:" in line and balance == "None":  # Ensure only the most recent balance is captured
            balance = extract_balance(line)
        if "STATUS:" in line and log_status == "None":  # Ensure only the most recent status is captured
            log_status = extract_status(line)
        if "Need to wait until" in line and next_claim_at == "None":  # Ensure only the most recent time is captured
            next_claim_at = parse_time_from_log(line)

    return (process_name, balance, next_claim_at, log_status)

def main():
    name_width = 20
    balance_width = 12
    claim_width = 20
    status_width = 80
    total_width = name_width + balance_width + claim_width + status_width + 9  # Added padding for the pipes and spaces

    print("Stopped Wallet Processes:\n")
    print("|-" + "-" * total_width + "-|")
    print(f"| {'Wallet Name'.ljust(name_width)} | {'Balance'.ljust(balance_width)} | {'Next Claim'.ljust(claim_width)} | {'Status'.ljust(status_width)} |")
    print("|-" + "-" * total_width + "-|")

    stopped_processes = run_command("pm2 list | grep stopped | awk '{print $4}'")
    results = [fetch_and_process_logs(name.strip(), "stopped") for name in stopped_processes.splitlines() if name.strip()]

    for result in results:
        name, balance, next_claim_at, status = result
        name = truncate_and_pad(name, name_width)
        balance = truncate_and_pad(balance, balance_width)
        next_claim_at = truncate_and_pad(next_claim_at, claim_width)
        status = truncate_and_pad(status, status_width)
        print(f"| {name} | {balance} | {next_claim_at} | {status} |")

    print("|-" + "-" * total_width + "-|")
    print("Running Wallet Processes:\n")
    print("|-" + "-" * total_width + "-|")
    print(f"| {'Wallet Name'.ljust(name_width)} | {'Balance'.ljust(balance_width)} | {'Next Claim'.ljust(claim_width)} | {'Status'.ljust(status_width)} |")
    print("|-" + "-" * total_width + "-|")

    running_processes = run_command("pm2 list | grep online | awk '{print $4}'")
    results = [fetch_and_process_logs(name.strip(), "online") for name in running_processes.splitlines() if name.strip()]

    for result in results:
        name, balance, next_claim_at, status = result
        name = truncate_and_pad(name, name_width)
        balance = truncate_and_pad(balance, balance_width)
        next_claim_at = truncate_and_pad(next_claim_at, claim_width)
        status = truncate_and_pad(status, status_width)
        print(f"| {name} | {balance} | {next_claim_at} | {status} |")

    print("|-" + "-" * total_width + "-|")

if __name__ == "__main__":
    main()