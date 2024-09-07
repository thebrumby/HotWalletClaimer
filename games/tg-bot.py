import os
import sys
import json
import asyncio
import logging
import subprocess
import requests
import re

from status import list_pm2_processes, list_all_pm2_processes, get_inactive_directories, get_logs_by_process_name, get_status_logs_by_process_name, fetch_and_process_logs, should_exclude_process

def download_file(url, dest):
    """Download a file from a URL to a destination path."""
    try:
        response = requests.get(url)
        response.raise_for_status()  # Ensure we notice bad responses
        with open(dest, 'wb') as f:
            f.write(response.content)
        print(f"Downloaded {url} to {dest}")
    except Exception as e:
        print(f"Failed to download {url}: {e}")
        sys.exit(1)

def modify_pull_games_script(script_path):
    """Modify the pull-games.sh script to suit our purpose."""
    script_content = """#!/bin/bash

# Define the target and source directories
TARGET_DIR="/app"
GAMES_DIR="$TARGET_DIR/games"
DEST_DIR="/usr/src/app/games"

# Check if the directory exists and is a git repository
if [ -d "$TARGET_DIR" ] && [ -d "$TARGET_DIR/.git" ]; then
    echo "$TARGET_DIR pulling latest changes."
    cd $TARGET_DIR
    git pull
elif [ -d "$TARGET_DIR" ] ; then
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
"""
    try:
        with open(script_path, 'w') as f:
            f.write(script_content)
        print(f"Modified {script_path} successfully.")
    except Exception as e:
        print(f"Failed to modify {script_path}: {e}")
        sys.exit(1)

def check_and_update_games_utils():
    """Check if games/utils exists, and if not, update using pull-games.sh."""
    if not os.path.exists("/usr/src/app/games/utils"):
        pull_games_dest = "/usr/src/app/pull-games.sh"

        # Check if pull-games.sh exists
        if os.path.exists(pull_games_dest):
            # Modify the pull-games.sh script
            modify_pull_games_script(pull_games_dest)

            # Make the script executable
            os.chmod(pull_games_dest, 0o755)

            # Run the pull-games.sh script
            result = subprocess.run([pull_games_dest], capture_output=True, text=True)
            if result.returncode != 0:
                print(f"Failed to execute {pull_games_dest}: {result.stderr}")
                sys.exit(1)
            else:
                print(f"Successfully executed {pull_games_dest}: {result.stdout}")
        else:
            print("pull-games.sh does not exist, skipping the update.")

# Ensure games/utils is present before proceeding with the imports
check_and_update_games_utils()

try:
    from telegram import (ReplyKeyboardMarkup, ReplyKeyboardRemove, Update,
                          InlineKeyboardButton, InlineKeyboardMarkup)
    from telegram.ext import (Application, CallbackQueryHandler, CommandHandler,
                              ContextTypes, ConversationHandler, MessageHandler, filters)
except ImportError:
    print("The 'python-telegram-bot' module is not installed. Installing it now...")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "python-telegram-bot"])
    from telegram import (ReplyKeyboardMarkup, ReplyKeyboardRemove, Update,
                          InlineKeyboardButton, InlineKeyboardMarkup)
    from telegram.ext import (Application, CallbackQueryHandler, CommandHandler,
                              ContextTypes, ConversationHandler, MessageHandler, filters)

try:
    from utils.pm2 import start_pm2_app, save_pm2
except ImportError:
    print("Failed to import PM2 utilities even after attempting to copy the necessary files and directories.")
    sys.exit(1)

from status import list_pm2_processes, list_all_pm2_processes, get_inactive_directories, get_logs_by_process_name, get_status_logs_by_process_name, fetch_and_process_logs

# Enable logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.INFO)

logger = logging.getLogger(__name__)

# Define states
COMMAND_DECISION, SELECT_PROCESS, PROCESS_DECISION, PROCESS_COMMAND_DECISION = range(4)

stopped_processes = []
running_processes = []
inactive_directories = []

selected_process = None

def load_telegram_token(file_path: str) -> str:
    """Load the telegram bot token from the specified file."""
    if not os.path.exists(file_path):
        logger.error(f"File {file_path} does not exist.")
        sys.exit(1)

    with open(file_path, 'r') as file:
        config = json.load(file)
    
    token = config.get("telegramBotToken")

    if token:
        logger.info(f"Token extracted: {token}")
        return token
    else:
        logger.error("telegramBotToken not found in the file.")
        sys.exit(1)

def run() -> None:
    """Run the bot."""
    token = load_telegram_token('variables.txt')
    if not token:
        sys.exit(1)

    application = Application.builder().token(token).build()

    # Add new commands as entry points
    conv_handler = ConversationHandler(
        entry_points=[
            CommandHandler('start', start),
            CommandHandler('list', list_games),
            CommandHandler('list_pattern', list_games_with_pattern),
            CommandHandler('start_game', start_game),
            CommandHandler('restart', restart_game),
            CommandHandler('stop', stop_game),
            CommandHandler('update', update_game_files)  # New command for updating
        ],
        states={
            COMMAND_DECISION: [CallbackQueryHandler(command_decision)],
            SELECT_PROCESS: [MessageHandler(filters.TEXT & ~filters.COMMAND, select_process)],
            PROCESS_DECISION: [CallbackQueryHandler(process_decision)],
            PROCESS_COMMAND_DECISION: [CallbackQueryHandler(process_command_decision)]
        },
        fallbacks=[CommandHandler('exit', exit),
           CommandHandler('list', list_games),
           CommandHandler('list_pattern', list_games_with_pattern),
           CommandHandler('start_game', start_game),
           CommandHandler('restart', restart_game),
           CommandHandler('stop', stop_game),
           CommandHandler('update', update_game_files)]  # Add fallback for the update command
    )

    application.add_handler(conv_handler)

    # Other global commands
    application.add_handler(CommandHandler("status", status_all))
    application.add_handler(CommandHandler("help", help))
    application.add_handler(CommandHandler("exit", exit))
    application.add_handler(CommandHandler('list', list_games))

    application.run_polling()

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Starts the conversation and asks the user about their preferred command type."""
    await update.message.reply_text(
        '<b>Telegram Claim Bot!\n'
        'How can I help you?</b>',
        parse_mode='HTML',
        reply_markup=ReplyKeyboardRemove(),
    )

    # Define inline buttons for car color selection
    keyboard = [
        [InlineKeyboardButton('ALL STATUS', callback_data='status')],
        [InlineKeyboardButton('SELECT PROCESS', callback_data='process')],
        [InlineKeyboardButton('Help', callback_data='help')],
        [InlineKeyboardButton('Exit', callback_data='exit')],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text('<b>Please choose:</b>', parse_mode='HTML', reply_markup=reply_markup)

    return COMMAND_DECISION

async def command_decision(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Asks the user to fill in the mileage or skip."""
    query = update.callback_query
    await query.answer()
    decision = query.data

    if decision == 'process':
        return await select_process(update, context)
    elif decision == 'status':
        return await status_all(update, context)
    elif decision == 'help':
        return await help(update, context)
    elif decision == 'exit':
        return await exit(update, context)
    else:
        await query.edit_message_text(f"Invalid command: {decision}")
        return ConversationHandler.END

async def help(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    return await send_message(update, context, """
    Available commands:
    /start - Start the original bot
    /status - Check the status of all processes
    /list - List all games
    /list_pattern <pattern> - List games matching a pattern
    /start <pattern> - Start processes matching the pattern
    /restart <pattern> - Restart processes matching the pattern
    /stop <pattern> - Stop processes matching the pattern
    /update - Update the game files (try pull-games.sh, then git pull)
    /help - Show this help message
    /exit - Exit the bot
    """)

async def exit(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Exit the bot."""
    return await send_message(update, context, "Goodbye!")

async def list_games(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """List all games, excluding unwanted and empty entries, and showing if they are running/stopped."""
    if context.args:
        # If there are arguments (a pattern), switch to pattern matching mode
        await list_games_with_pattern(update, context)
    else:
        # Otherwise, list all games
        games = list_all_pm2_processes()
        running_processes = list_pm2_processes("online")  # Get running processes

        for game in games:
            # Exclude processes that match excluded keywords
            if should_exclude_process(game.strip()):
                continue  # Skip this process if it's in the exclusion list

            # Fetch and process logs for each game
            name, balance, _, _, status = fetch_and_process_logs(game.strip())

            # Filter out empty or incomplete entries
            if not name or balance == "None" or status == "Log file missing":
                continue  # Skip if the entry is incomplete

            # Determine if the process is running or stopped
            process_state = "Running" if game.strip() in running_processes else "Stopped"

            # Send each game's details as a separate message
            response = f"Session Name: {name}\nBalance: {balance}\nStatus: {status}\nState: {process_state}\n"
            await send_message(update, context, response)

async def list_games_with_pattern(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """List games matching a pattern, excluding certain processes and showing if they are running/stopped."""
    if not context.args:
        await send_message(update, context, "Please provide a pattern to match.")
        return

    pattern = context.args[0]
    games = list_all_pm2_processes()  # Get all PM2 processes
    running_processes = list_pm2_processes("online")  # Get running processes
    response = ""

    for game in games:
        # Exclude processes that match excluded keywords
        if should_exclude_process(game.strip()):
            continue

        # Check if the pattern matches the session name (case-insensitive)
        if re.search(pattern, game.strip(), re.IGNORECASE):
            name, balance, _, _, status = fetch_and_process_logs(game.strip())

            # Filter out empty or incomplete entries
            if not name or balance == "None" or status == "Log file missing":
                continue  # Skip if the entry is incomplete

            # Determine if the process is running or stopped
            process_state = "Running" if game.strip() in running_processes else "Stopped"

            # Build the response
            response += f"Session Name: {name}\nBalance: {balance}\nStatus: {status}\nState: {process_state}\n\n"

    if not response:
        response = f"No games found matching the pattern: {pattern}"

    await send_message(update, context, response)

async def manage_process(update: Update, context: ContextTypes.DEFAULT_TYPE, action: str):
    """Manage processes (start/restart/stop) using PM2 and provide feedback."""
    if not context.args:
        await send_message(update, context, f"Usage: /{action} <pattern>")
        return
    
    pattern = context.args[0]  # Get the pattern provided by the user
    games = list_all_pm2_processes()  # Fetch all processes from PM2

    # Find processes that match the given pattern
    matched_games = [game for game in games if re.search(pattern, game)]

    if not matched_games:
        await send_message(update, context, f"No matching processes found for pattern: {pattern}")
        return

    # For each matched process, execute the desired PM2 action and provide feedback
    for game in matched_games:
        command = f"pm2 {action} {game.strip()}"
        result = await run_command(command)  # Run the PM2 command and capture the result

        # Send feedback to the user in Telegram
        if "Process not found" in result:
            await send_message(update, context, f"Process not found: {game.strip()}")
        else:
            # Adjust feedback based on the action performed
            if action == "start":
                await send_message(update, context, f"Successfully started: {game.strip()}")
            elif action == "restart":
                await send_message(update, context, f"Successfully restarted: {game.strip()}")
            elif action == "stop":
                await send_message(update, context, f"Successfully stopped: {game.strip()}")

async def update_game_files(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Update the game files by trying pull-games.sh first, then git pull if that fails."""
    pull_games_script = "./pull-games.sh"
    
    # Check if pull-games.sh exists
    if os.path.exists(pull_games_script):
        # Try to run pull-games.sh
        result = await run_command(pull_games_script)
        if "not found" in result.lower() or "failed" in result.lower():
            await send_message(update, context, "Failed to execute pull-games.sh. Attempting git pull...")
            # Attempt git pull if pull-games.sh fails
            git_result = await run_git_pull(update, context)
            return
        else:
            await send_message(update, context, f"pull-games.sh executed successfully:\n{result}")
    else:
        await send_message(update, context, "pull-games.sh not found. Attempting git pull...")
        # Attempt git pull if pull-games.sh does not exist
        git_result = await run_git_pull(update, context)

async def run_git_pull(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Run git pull and handle output within the 4k message size limit."""
    git_result = await run_command("git pull")
    
    if "error" in git_result.lower() or "aborting" in git_result.lower():
        # If there are errors, capture and send the error result
        await send_limited_message(update, context, git_result)
    else:
        # If it's a success, send the update result
        await send_limited_message(update, context, git_result)

async def run_command(command: str) -> str:
    """Execute a shell command and return its output including both stdout and stderr."""
    proc = await asyncio.create_subprocess_shell(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )
    stdout, stderr = await proc.communicate()

    # Combine stdout and stderr into one response to capture all output
    return stdout.decode() + "\nError: " + stderr.decode()

async def send_limited_message(update: Update, context: ContextTypes.DEFAULT_TYPE, text: str, limit: int = 4096):
    """Send messages in chunks limited to 4k characters."""
    # Split the text into chunks of 4096 characters and send each as a separate message
    for i in range(0, len(text), limit):
        await send_message(update, context, text[i:i + limit])

async def send_message(update: Update, context: ContextTypes.DEFAULT_TYPE, text: str) -> int:
    """Send a message with the help of the bot."""
    if update.callback_query:
        chat_id = update.callback_query.message.chat_id
        await context.bot.send_message(chat_id=chat_id, text=text, parse_mode='HTML')
        await update.callback_query.answer()
    elif update.message:
        await update.message.reply_text(text)

# Handlers for /start, /restart, /stop
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Start the bot or handle process start based on provided arguments."""
    # Check if there are any arguments (i.e., /start <pattern>)
    if context.args:
        # If arguments are provided, assume it's for starting a specific process
        await manage_process(update, context, "start")
        return ConversationHandler.END
    else:
        # No arguments provided, start the bot's conversation as usual
        await update.message.reply_text(
            '<b>Telegram Claim Bot!\n'
            'How can I help you?</b>',
            parse_mode='HTML',
            reply_markup=ReplyKeyboardRemove(),
        )

        # Define inline buttons for bot options
        keyboard = [
            [InlineKeyboardButton('ALL STATUS', callback_data='status')],
            [InlineKeyboardButton('SELECT PROCESS', callback_data='process')],
            [InlineKeyboardButton('Help', callback_data='help')],
            [InlineKeyboardButton('Exit', callback_data='exit')],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text('<b>Please choose:</b>', parse_mode='HTML', reply_markup=reply_markup)

        return COMMAND_DECISION

async def restart_game(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await manage_process(update, context, "restart")

async def stop_game(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await manage_process(update, context, "stop")

async def start_game(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start a process based on a pattern using the manage_process function."""
    await manage_process(update, context, "start")

#region Unique Process

async def select_process(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    global stopped_processes, running_processes, inactive_directories

    await get_processes()

    """Select a process to run."""
    query = update.callback_query

    keyboard = []

    print("Stopped Processes: " + ', '.join(stopped_processes))
    print("Running Processes: " + ', '.join(running_processes))
    print("Inactive Directories: " + ', '.join(inactive_directories))

    for process in stopped_processes:
        keyboard.append([InlineKeyboardButton(process + u" 🔴", callback_data=process)])

    for process in running_processes:
        keyboard.append([InlineKeyboardButton(process + u" 🟢", callback_data=process)])

    for directory in inactive_directories:
        keyboard.append([InlineKeyboardButton(directory + u" ⚫", callback_data=directory)])

    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.message.reply_text('<b>Choose an option:</b>', parse_mode='HTML', reply_markup=reply_markup)

    return PROCESS_DECISION

async def process_decision(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    global selected_process

    """Asks the user to fill in the mileage or skip."""
    query = update.callback_query
    await query.answer()
    selected_process = query.data

    # Define inline buttons for car color selection
    keyboard = [
        [InlineKeyboardButton('STATUS', callback_data='status')],
        [InlineKeyboardButton('LOGS', callback_data='logs')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.message.reply_text('<b>Please choose:</b>', parse_mode='HTML', reply_markup=reply_markup)

    return PROCESS_COMMAND_DECISION

async def process_command_decision(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Asks the user to fill in the mileage or skip."""
    query = update.callback_query
    await query.answer()
    decision = query.data

    if decision == 'status':
        return await status_process(update, context)
    elif decision == 'logs':
        return await logs_process(update, context)
    else:
        await query.edit_message_text(f"Invalid command: {decision}")
        return ConversationHandler.END

async def status_process(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Send a message with the status of the bot."""

    logs = get_status_logs_by_process_name(selected_process)
    await send_message(update, context, (f"{logs}." if logs != "" else f"The process {selected_process} was not found."))
    return ConversationHandler.END

async def logs_process(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Send a message with the status of the bot."""

    logs = get_logs_by_process_name(selected_process)
    await send_message(update, context, (f"{logs}." if logs != "" else f"The process {selected_process} was not found."))
    return ConversationHandler.END

def find_index(lst, value):
    for i, v in enumerate(lst):
        if v == value:
            return i
    return -1

#endregion

#region All Processes

async def status_all(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    global stopped_processes, running_processes, inactive_directories

    await get_processes()

    for process in stopped_processes:
        if not should_exclude_process(process):
            await send_message(update, context, show_logs(process.strip()))

    for process in running_processes:
        if not should_exclude_process(process):
            await send_message(update, context, show_logs(process.strip()))

    for directory in inactive_directories:
        if not should_exclude_process(directory):
            await send_message(update, context, show_logs(directory.strip()))

    return ConversationHandler.END

def should_exclude_process(process_name):
    excluded_keywords = ["solver-tg-bot", "Telegram", "http-proxy", "Activating", "Initialising"]
    return any(keyword in process_name for keyword in excluded_keywords)

def show_logs(process) -> str:
    """Send a message with the status of the bot."""

    try:
        name, balance, profit_hour, next_claim_at, log_status = fetch_and_process_logs(process.strip())
        return f"{name}\n\tBALANCE: {balance}\n\tPROFIT/HOUR: {profit_hour}\n\tNEXT CLAIM AT: {next_claim_at}\n\tLOG STATUS:\n\t{log_status}"
    except Exception as e:
        print(f"Error: {e}")
        return f"{process}: ERROR getting information."

#endregion

#region Utils

async def send_message(update: Update, context: ContextTypes.DEFAULT_TYPE, text: str) -> int:
    """Send a message with the help of the bot."""

    # Determine the correct way to send a reply based on the update type
    if update.callback_query:
        # If called from a callback query, use the callback_query's message
        chat_id = update.callback_query.message.chat_id
        await context.bot.send_message(chat_id=chat_id, text=text, parse_mode='HTML')
        # Optionally, you might want to acknowledge the callback query
        await update.callback_query.answer()
    elif update.message:
        # If called from a direct message
        await update.message.reply_text(text)
    else:
        # Handle other cases or log an error/warning
        logger.warning('skip_mileage was called without a message or callback_query context.')

async def get_processes():
    global stopped_processes, running_processes, inactive_directories

    stopped_processes = list_pm2_processes("stopped")
    running_processes = list_pm2_processes("online")
    inactive_directories = get_inactive_directories()

#endregion

def main() -> None:
    token = load_telegram_token('variables.txt')
    if not token:
        sys.exit(1)

    if not os.path.exists("/usr/src/app/games/utils"):
        pull_games_dest = "/usr/src/app/pull-games.sh"

        # Check if pull-games.sh exists
        if os.path.exists(pull_games_dest):
            # Modify the pull-games.sh script
            modify_pull_games_script(pull_games_dest)

            # Make the script executable
            os.chmod(pull_games_dest, 0o755)

            # Run the pull-games.sh script
            result = subprocess.run([pull_games_dest], capture_output=True, text=True)
            if result.returncode != 0:
                print(f"Failed to execute {pull_games_dest}: {result.stderr}")
                sys.exit(1)
            else:
                print(f"Successfully executed {pull_games_dest}: {result.stdout}")
        else:
            print("pull-games.sh does not exist, skipping the update.")

    list_pm2_processes = set(list_all_pm2_processes())

    if "Telegram-Bot" not in list_pm2_processes:
        script = "games/tg-bot.py"

        pm2_session = "Telegram-Bot"
        print(f"You could add the new/updated session to PM use: pm2 start {script} --interpreter venv/bin/python3 --name {pm2_session} -- {pm2_session}", 1)
        user_choice = input("Enter 'e' to exit, 'a' or <enter> to automatically add to PM2: ").lower()

        if user_choice == "e":
            print("Exiting script. You can resume the process later.", 1)
            sys.exit()
        elif user_choice == "a" or not user_choice:
            start_pm2_app(script, pm2_session, pm2_session)
            user_choice = input("Should we save your PM2 processes? (Y/n): ").lower()
            if user_choice == "y" or not user_choice:
                save_pm2()
            print(f"You can now watch the session log into PM2 with: pm2 logs {pm2_session}", 2)
            sys.exit()

    run()

if __name__ == '__main__':
    main()
