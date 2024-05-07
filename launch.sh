#!/bin/bash

# Function to activate the virtual environment
activate_venv() {
    echo "Activating virtual environment..."
    source venv/bin/activate
}

# Function to deactivate the virtual environment
deactivate_venv() {
    echo "Deactivating virtual environment..."
    deactivate
}

# Function to run the python script
run_script() {
    local script=$1
    echo "Running script: $script"
    python3 "$script"
}

# Function to list and choose a script
list_and_choose_script() {
    echo "Listing available Telegram Claim Assistant scripts:"
    # List all python scripts in the current directory
    IFS=$'\n' read -d '' -r -a scripts < <(find . -maxdepth 1 -name "*.py" -print && printf '\0')
    
    if [ ${#scripts[@]} -eq 0 ]; then
        echo "No Python scripts found in the current directory."
        exit 1
    fi

    # Enumerate all found scripts
    for i in "${!scripts[@]}"; do
        echo "$((i+1))) ${scripts[$i]}"
    done

    # Prompt user to select a script
    echo "Please select a script by number:"
    read -r choice
    selected_script="${scripts[$((choice-1))]}"
    
    if [ -n "$selected_script" ]; then
        activate_venv
        run_script "$selected_script"
        deactivate_venv
    else
        echo "Invalid selection. Exiting..."
        exit 1
    fi
}

# Check if the script argument is provided
if [ -z "$1" ]; then
    list_and_choose_script
else
    # Append '.py' if it is not present in the script name
    script_name="$1"
    if [[ ! "$script_name" == *".py" ]]; then
        script_name="${script_name}.py"
    fi

    # Check if the script exists in the current directory
    if [ -f "$script_name" ]; then
        activate_venv
        run_script "$script_name"
        deactivate_venv
    else
        echo "Specified script not found."
        list_and_choose_script
    fi
fi