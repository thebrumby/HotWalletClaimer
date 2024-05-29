#!/bin/bash

while true; do
    # Run the pull-games.sh script
    ./pull-games.sh

    # Display the current time and date
    echo "Script executed at: $(date)"

    # Idle for 24 hours
    sleep 43200  # 43200 seconds = 12 hours
done