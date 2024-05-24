#!/bin/bash

# Function to remove directories
remove_directories() {
    local dir_name="$1"
    echo "Removing directories for $dir_name..."
    rm -rf "./selenium/$dir_name"
    rm -rf "./backups/$dir_name"
    rm -rf "./screenshots/$dir_name"
    echo "Removed directories for $dir_name"
}

# Function to list and enumerate all PM2 processes
list_pm2_processes() {
    pm2 list --no-color | awk 'NR>4 && !/^$/ {print NR-4". "$4}'
}

# Function to get inactive directories
get_inactive_directories() {
    local all_sessions=()
    while IFS= read -r -d '' session; do
        all_sessions+=("$session")
    done < <(find ./selenium -mindepth 1 -maxdepth 1 -type d -print0)

    local inactive_sessions=()
    for session_path in "${all_sessions[@]}"; do
        session=$(basename "$session_path")
        pm2 describe "$session" &> /dev/null
        if [ $? -ne 0 ]; then
            inactive_sessions+=("$session")
        fi
    done

    echo "${inactive_sessions[@]}"
}

# Function to list and enumerate inactive directories
list_inactive_directories() {
    local inactive_sessions=($(get_inactive_directories))
    if [ ${#inactive_sessions[@]} -eq 0 ]; then
        echo "There are no folders not associated with a running process."
        return 1
    else
        for i in "${!inactive_sessions[@]}"; do
            echo "$((i+1)). ${inactive_sessions[$i]}"
        done
    fi
}

# Main script starts here
while true; do
    echo "Choose an option:"
    echo "1. Remove an active session"
    echo "2. Remove inactive folders"
    echo "3. Exit"
    read -rp "Enter your choice [1-3]: " choice

    case $choice in
        1)
            if [ $(pm2 list --no-color | awk 'NR>4 && !/^$/ {print $4}' | wc -l) -eq 0 ]; then
                echo "There are no active processes."
                continue
            fi

            while true; do
                echo "Listing all PM2 processes:"
                list_pm2_processes
                read -rp "Enter the number of the process to remove, or type 'back' to go back: " proc_number
                
                if [[ "$proc_number" == "back" ]]; then
                    echo "Going back to the main menu."
                    break
                fi
                
                process_name=$(pm2 list --no-color | awk "NR==$(($proc_number+4)) {print \$4}")
                if [ -z "$process_name" ]; then
                    echo "Invalid process number."
                    continue
                fi
                
                pm2 stop "$process_name" &> /dev/null
                pm2 delete "$process_name" &> /dev/null
                pm2 save &> /dev/null
                echo "Stopped and deleted process $process_name from PM2."
                
                remove_directories "$process_name"
                break
            done
            ;;
        2)
            while true; do
                echo "Listing all inactive directories:"
                if ! list_inactive_directories; then
                    break
                fi
                read -rp "Enter the number of the directory to remove, 'all' to remove all except Telegram, or 'back' to go back: " dir_input
                
                inactive_sessions=($(get_inactive_directories))
                total_sessions=${#inactive_sessions[@]}

                if [[ "$dir_input" == "all" ]]; then
                    echo "Removing all inactive directories except those starting with 'Telegram:'..."
                    for dir in "${inactive_sessions[@]}"; do
                        if [[ $dir != Telegram:* ]]; then
                            remove_directories "$dir"
                        fi
                    done
                    break
                elif [[ "$dir_input" == "back" ]]; then
                    echo "Going back to the main menu."
                    break
                elif [[ "$dir_input" =~ ^[0-9]+$ && "$dir_input" -gt 0 && "$dir_input" -le "$total_sessions" ]]; then
                    dir_name=${inactive_sessions[$(($dir_input-1))]}
                    remove_directories "$dir_name"
                else
                    echo "Invalid choice. Please enter a valid number, 'all', or 'back'."
                fi
            done
            ;;
        3)
            echo "Exiting."
            exit 0
            ;;
        *)
            echo "Invalid choice. Please enter 1, 2, or 3."
            ;;
    esac
done