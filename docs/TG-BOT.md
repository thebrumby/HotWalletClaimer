# Setting Up a Relay from this Script to a Telegram Bot

## Step 1: Create a Telegram Bot Using BotFather

1. **Search for BotFather** in your Telegram client or use this link: [BotFather](https://t.me/botfather).

2. **Create a New Bot**:
   - Start a chat with BotFather.
   - Enter the command `/newbot`.
   - Follow the instructions to name your bot and give it a unique username.
   - **Copy the token** provided by BotFather. This token will be used to access the HTTP API for your bot. **Keep this token secure**, as anyone with access to it can control your bot.

3. **Send a Message to Your New Bot**:
   - Visit your bot's URL given by the BotFather, which will be something like `https://t.me/myBotName_bot`.
   - Type "Hello" and press enter to send the message. This initializes a chat that our script will use.

## Step 2: Configure the Script to Use the Telegram Bot

4. **Launch Any Game and Select `y` to Edit the Settings**:
   - For example, run `./launch.sh hot`.
   - Scroll through the options by hitting Enter until you reach the "Telegram verbose level" option.
   - Choose a level of detail between 0 (no updates pushed) to 3 (every small step pushed). For most users, level 1 is a good choice.
   - Continue to scroll down until you reach "Enter the Telegram Bot Token" and enter the access token from BotFather.
   - Keep hitting Enter until all settings have been cycled through and the revised settings are shown.
   - At this point, you can either set up a new game session or press Ctrl+C to exit.
   - With these steps completed, each game session restarted with the updated settings will push updates to your bot.

5. **Set Up Additional Interaction with Your Telegram Bot**:
   - Run `./launch.sh tg-bot` to add an additional level of interaction between your game sessions and the Telegram bot.
   - This script will set up a PM2 process to monitor for requests from you in Telegram.
   - Once set up, you can use commands like `/start`, `/help`, `/status`, `/logs`, and `/exit` to pull additional information for each game session by choosing the links from the list of options.

By following these steps, you'll have a fully configured relay from your script to your Telegram bot, allowing you to receive updates and interact with your game sessions via Telegram.

**Massive thanks to community member JBR1999 for developing and contributing this code!**

### Available Commands:

- `/start` - Start the original bot
- `/status` - Check the status of all processes
- `/list` - List all games
- `/list_pattern <pattern>` - List games matching a pattern
- `/start <pattern>` - Start processes matching the pattern
- `/restart <pattern>` - Restart processes matching the pattern
- `/stop <pattern>` - Stop processes matching the pattern
- `/update` - Update the game files (try `pull-games.sh`, then `git pull`)
- `/help` - Show this help message
- `/exit` - Exit the bot
