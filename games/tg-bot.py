import os
import sys
import json
import asyncio
import logging
import subprocess
import shutil

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
    # If import fails, execute the copy sequence
    if not os.path.exists("/usr/src/app/games/utils"):
        if os.path.exists("/app/docker/pull-games.sh"):
            shutil.move("/app/docker/pull-games.sh", "/usr/src/app/pull-games.sh")
            os.chmod("/usr/src/app/pull-games.sh", 0o755)
            os.system("/usr/src/app/pull-games.sh")

    # Retry importing after copying
    try:
        from utils.pm2 import start_pm2_app, save_pm2
    except ImportError:
        print("Failed to import PM2 utilities even after attempting to copy the pull-games.sh script.")
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

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start)],
        states={
            COMMAND_DECISION: [CallbackQueryHandler(command_decision)],
            SELECT_PROCESS: [MessageHandler(filters.TEXT & ~filters.COMMAND, select_process)],
            PROCESS_DECISION: [CallbackQueryHandler(process_decision)],
            PROCESS_COMMAND_DECISION: [CallbackQueryHandler(process_command_decision)]
        },
        fallbacks=[CommandHandler('exit', exit)],
    )

    application.add_handler(conv_handler)

    # Handle the case when a user sends /start but they're not in a conversation
    application.add_handler(CommandHandler('start', start))
    application.add_handler(CommandHandler("status", status_all))
    application.add_handler(CommandHandler("help", help))
    application.add_handler(CommandHandler("exit", exit))

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
    """Send a message with the help of the bot."""
    return await send_message(update, context, "Available commands:\n/start - Start the bot\n/status - Check the status of all processes\n/help - Show this help message\n/exit - Exit the bot")

async def exit(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Exit the bot."""
    return await send_message(update, context, "Goodbye!")

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
    global stopped_processes, running_processes, inactive_directories, stopped_process_list, running_process_list

    await get_processes()

    for process in stopped_processes:
        await send_message(update, context, show_logs(process.strip()))

    for process in running_processes:
        await send_message(update, context, show_logs(process.strip()))

    for directory in inactive_directories:
        await send_message(update, context, show_logs(directory.strip()))

    return ConversationHandler.END

def show_logs(process) -> str:
    """Send a message with the status of the bot."""

    try:
        name, balance, next_claim_at, log_status = fetch_and_process_logs(process.strip())
        return f"{name}:\n\t BALANCE: {balance}\n\tNEXT CLAIM AT: {next_claim_at}\n\tLOG STATUS: {log_status}"
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

async def run_command(command: str) -> str:
    """Execute a shell command and return its output."""
    proc = await asyncio.create_subprocess_shell(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )
    stdout, stderr = await proc.communicate()
    if stderr:
        print(f"Error: {stderr.decode()}")
    return stdout.decode()

if __name__ == '__main__':
    main()
