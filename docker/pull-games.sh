#!/bin/bash

# Define the target and source directories
TARGET_DIR="/app"
GAMES_DIR="$TARGET_DIR/games"
DEST_DIR="/usr/src/app/games"

# Check if the directory exists and is a git repository
if [ -d "$TARGET_DIR" ] && [ -d "$TARGET_DIR/.git" ]; then
    echo "$TARGET_DIR pulling latest changes."
    cd $TARGET_DIR
    git pull
elif [ -d "$TARGET_DIR" ]; then
    echo "$TARGET_DIR exists but is not a git repository. Removing and cloning afresh."
    rm -rf $TARGET_DIR
    git clone https://github.com/thebrumby/HotWalletClaimer.git $TARGET_DIR
else
    echo "$TARGET_DIR does not exist. Cloning repository."
    git clone https://github.com/thebrumby/HotWalletClaimer.git $TARGET_DIR
fi

# Set the working directory to the cloned repository
cd $GAMES_DIR

# Create the destination directory
mkdir -p $DEST_DIR

# Copy Python scripts to the destination directory if they exist and are newer
if ls *.py 1> /dev/null 2>&1; then
    for file in *.py; do
        # Check if the destination file exists and compare modification times
        if [ -f "$DEST_DIR/$file" ]; then
            if [ "$file" -nt "$DEST_DIR/$file" ]; then
                cp "$file" "$DEST_DIR"
                echo "Updated $file"
            else
                echo "$file is already up-to-date."
            fi
        else
            cp "$file" "$DEST_DIR"
            echo "Copied new file $file"
        fi
    done
else
    echo "No Python scripts found to copy."
fi