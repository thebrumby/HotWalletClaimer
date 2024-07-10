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

# Copy the contents of the games directory recursively
cp -r $GAMES_DIR/* $DEST_DIR

echo "All files and subdirectories have been copied to $DEST_DIR"
