import subprocess
from datetime import datetime

def run_command(command):
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
    string = string or "None"
    return (string[:length-3] + '...').ljust(length) if len(string) > length else string.ljust(length)

def extract_detail(line, keyword):
    return line.split(f"{keyword}:")[1].strip() if keyword in line else "None"

def fetch_and_process_logs(process_name):
    sanitized_process_name = process_name.replace(':', '-')
    log_file = f"/root/.pm2/logs/{sanitized_process_name}-out.log"
    logs = run_command(f"tail -n 200 {log_file}")

    balance = "None"
    next_claim_at = "None"
    log_status = "None"

    relevant_lines = [line for line in reversed(logs.splitlines()) if any(kw in line for kw in ["BALANCE:", "STATUS:", "Need to wait until"])]

    for line in relevant_lines:
        if "BALANCE:" in line and balance == "None":
            balance = extract_detail(line, "BALANCE")
        if "STATUS:" in line and log_status == "None":
            log_status = extract_detail(line, "STATUS")
        if "Need to wait until" in line and next_claim_at == "None":
            next_claim_at = parse_time_from_log(line)

    return process_name, balance, next_claim_at, log_status

def display_processes(processes, status):
    name_width = 20
    balance_width = 12
    claim_width = 20
    status_width = 80
    total_width = name_width + balance_width + claim_width + status_width + 9

    print(f"{status} Wallet Processes:\n")
    print("|-" + "-" * total_width + "-|")
    print(f"| {'Wallet Name'.ljust(name_width)} | {'Balance'.ljust(balance_width)} | {'Next Claim'.ljust(claim_width)} | {'Status'.ljust(status_width)} |")
    print("|-" + "-" * total_width + "-|")

    for process_name in processes.splitlines():
        if process_name.strip():
            name, balance, next_claim_at, log_status = fetch_and_process_logs(process_name.strip())
            name = truncate_and_pad(name, name_width)
            balance = truncate_and_pad(balance, balance_width)
            next_claim_at = truncate_and_pad(next_claim_at, claim_width)
            log_status = truncate_and_pad(log_status, status_width)
            print(f"| {name} | {balance} | {next_claim_at} | {log_status} |")

    print("|-" + "-" * total_width + "-|")

def main():
    stopped_processes = run_command("pm2 list | grep stopped | awk '{print $4}'")
    display_processes(stopped_processes, "Stopped")

    running_processes = run_command("pm2 list | grep online | awk '{print $4}'")
    display_processes(running_processes, "Running")

if __name__ == "__main__":
    main()