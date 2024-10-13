#!/bin/bash

# Function to prompt for sleep time in seconds
get_sleep_time() {
    while true; do
        read -p "Enter the wait time between starting batches of processes (in seconds): " sleep_seconds
        # Check if input is a positive integer
        if [[ "$sleep_seconds" =~ ^[1-9][0-9]*$ ]]; then
            echo "Wait time set to $sleep_seconds second(s)."
            break
        else
            echo "Invalid input. Please enter a positive integer value for seconds."
        fi
    done
}

# Function to prompt for number of processes per batch
get_batch_size() {
    while true; do
        read -p "Enter the number of processes to start before applying the wait timer: " batch_size
        # Check if input is a positive integer
        if [[ "$batch_size" =~ ^[1-9][0-9]*$ ]]; then
            echo "Batch size set to $batch_size process(es) per batch."
            break
        else
            echo "Invalid input. Please enter a positive integer value for the number of processes."
        fi
    done
}

# Function to check if an element is in an array
contains_element () {
    local element
    for element in "${@:2}"; do
        if [[ "$element" == "$1" ]]; then
            return 0
        fi
    done
    return 1
}

# Prompt the user for sleep time and batch size
get_sleep_time
get_batch_size

# Ensure 'jq' is installed for JSON parsing
if ! command -v jq &> /dev/null
then
    echo "'jq' is required but not installed. Installing jq..."
    sudo apt-get update
    sudo apt-get install -y jq
fi

# Get a list of stopped PM2 processes
stopped_processes=$(pm2 jlist | jq -r '.[] | select(.pm2_env.status=="stopped") | .name')

# Define initial processes to start
initial_processes=("solver-tg-bot" "http-proxy" "Telegram-Bot")

# Convert stopped_processes to an array
IFS=$'\n' read -rd '' -a stopped_array <<<"$stopped_processes"

# Start initial PM2 processes if they are in the stopped list
for process in "${initial_processes[@]}"; do
    if contains_element "$process" "${stopped_array[@]}"; then
        echo "Starting $process..."
        pm2 start "$process"
        # Remove the process from stopped_array
        stopped_array=("${stopped_array[@]/$process}")
        echo "$process started."
    else
        echo "$process is not in the stopped list or is already running."
    fi
done

# Reconstruct stopped_processes from the updated array
stopped_processes=$(printf "%s\n" "${stopped_array[@]}" | grep -v '^$')

# Check if there are any stopped processes left
if [ -z "$stopped_processes" ]; then
    echo "No additional stopped PM2 processes found."
else
    echo "Found the following stopped PM2 processes:"
    echo "$stopped_processes"

    # Convert stopped_processes to an array
    IFS=$'\n' read -rd '' -a process_array <<<"$stopped_processes"

    total_processes=${#process_array[@]}
    echo "Total stopped processes to start: $total_processes"

    # Initialize counters
    count=0
    started=0

    for process in "${process_array[@]}"; do
        echo "Restarting process: $process"
        pm2 restart "$process"
        echo "Started $process."
        ((started++))
        ((count++))

        # If count reaches batch_size and there are more processes to start, wait
        if (( count == batch_size && started < total_processes )); then
            echo "Reached batch size of $batch_size. Waiting for $sleep_seconds second(s) before starting the next batch..."
            sleep "$sleep_seconds"
            count=0  # Reset count for the next batch
        fi
    done
fi

# Reset all PM2 logs
echo "Resetting all PM2 logs..."
pm2 reset all

# Save the current PM2 process list
echo "Saving PM2 process list..."
pm2 save

echo "All stopped processes have been handled."