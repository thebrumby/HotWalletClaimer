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

# Function to run the Python script with additional arguments
run_script() {
    local script=$1
    shift  # Shift past the script name to get any additional parameters
    echo "Running script: $script with arguments: $@"
    python3 "$script" "$@"
}

# Function to list and choose a script
list_and_choose_script() {
    echo "Listing available scripts in the current directory and ./games folder:"
    # List all Python scripts in the current directory and ./games directory
    IFS=$'\n' read -d '' -r -a scripts < <(find . ./games -maxdepth 1 -name "*.py" -print && printf '\0')
    
    if [ ${#scripts[@]} -eq 0 ]; then
        echo "No Python scripts found in the current directory or ./games directory."
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
        run_script "$selected_script" "${@:2}"
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

    # Check if the script exists in the ./games directory or current directory
    if [ -f "./games/$script_name" ]; then
        script_path="./games/$script_name"
    elif [ -f "$script_name" ]; then
        script_path="$script_name"
    else:
        echo "Specified script not found in the ./games directory or current directory."
        list_and_choose_script
        exit 1
    fi

    activate_venv
    run_script "$script_path" "${@:2}"
    deactivate_venv
fi