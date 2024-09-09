# Troubleshooting Guide:
### Please follow this guide in addition to the main instructions, walkthrough videos, and documentation before raising a support ticket.

Before raising an issue, please be aware that many reported problems are often linked to common issues such as search queries blocking the GUI, running outdated code, becoming logged out of Telegram, or incorrect use of the script. To help us assist you more efficiently and minimize the time spent on support, we encourage you to follow all relevant steps in this troubleshooting guide.

From time to time, games update their Graphical User Interface (GUI) or add new screens or in-game challenges that may require adjustments to the script. In such cases, it would be appreciated if you raise an issue to ensure we are aware of the issue - in this situation, screenshots of the issue are always beneficial.

> **Note:** We now use a template format to direct users to self-help guides and troubleshooting. When raising a ticket, make sure to clearly outline what steps you've already taken. Issues raised with no evidence of following this guide may be closed without further action.

## Ensure Your Script is Up-to-Date

Before raising an issue, check the status of the script you're experiencing problems with by using [this table](https://github.com/thebrumby/HotWalletClaimer/blob/main/docs/LAUNCHCOMMANDS.md) to ensure there are no known bugs and that your local copy of the script is up-to-date. We frequently update the code, and if a problem has affected other users, chances are a fix has already been deployed. Running an outdated version of the code may cause you to experience issues that have already been resolved.

> **Note:** Docker-based installs automatically pull the latest code every 12 hours. However, if an error was briefly introduced into the code, your install might have automatically pulled the faulty version before the fix was applied. Manually checking that you're up-to-date before raising a support ticket can save time for both you and the development team.

### On Docker:
Ensure you are inside the container and run this command:
```
./pull-scripts.sh
```

### On a stand-alone installation:
Navigate to the **`HotWalletBot`** directory, or the location of your local installation, by using the change directory command (`cd`), and then execute:

```
git pull
```

## Check the GUI in Telegram Web (https://web.telegram.org/):
1. Ensure to use the web version of Telegram, as this is the version used by the script. The fact it is working in your mobile or desktop app does not guarantee it is working in the web version. Game developers frequently block this version to deter automated claiming.
2. Is the game working correctly or under maintenance? The script can only interact with a game that is working as expected and that humans can interact with.
3. Are you being challenged by Cloudflare? This can often block the script from claiming, although sometimes selecting the option to use the same user agent as you are using in the GUI may help. Most games that enable Cloudflare often remove it after a few weeks (perhaps due to cost).
4. Can you manually trigger a claim? Games get bugs too - check there are no error messages when manually triggering a claim and that there is no in-game lag. Sometimes games like Hexacore show you are clicking the cube, but when the screen is refreshed, it never registers your progress.
5. Is there anything in the search bar that might be blocking the script from accessing the game window?
6. If all else fails with the solutions below, consider deleting the current chat with the bot in the Telegram GUI and starting with a fresh chat. Failing that, if you are using a saved Telegram session, renew it. These two actions can remove any blocks that are preventing the script from working.

## Ensure you have sufficient Gas Fee
Games such as Hot, Cold, and Ocean/Sui mine your rewards directly onto the blockchain and consume a small amount of the network base token as a gas fee with each claim. For example, in the case of Hot, you must hold more than 0.1 NEAR to avoid the transaction being rejected by the game. This acts as a minimum balance requirement to ensure you have enough funds to cover transaction costs. While the game requires this higher balance, the network will only deduct the standard gas fee for each transaction.

## Enable debugging:
1. Open the script using **`./launch.sh`** as if you wish to create a new game session (more advanced users may prefer to directly edit the settings in **`variables.txt`**).
2. Edit the settings and enable the “Debug” option by choosing 'y.' If editing variables.txt, set **`"debugIsOn": true`**. Enabling this option saves step-by-step screenshots of your claim attempts.
3. Restart any session that is stuck:
```
pm2 restart [process name]
```
Example:
```
pm2 restart HOT:Wallet1
# Or use pattern matching
pm2 restart /Hot/
```
4. Open the screenshots from the file browser of ShellNGN, the explorer pane of WinSCP, or your preferred file transfer client. You will need to navigate inside the installation folder to the **`screenshots`** directory and then to the directory with the same name as your stuck game session. Each saved screenshot will be prefixed by the step number visible in PM2 logs.
5. If you are using Docker, the easiest way to view the screenshots is to copy them into your local environment file system:
```
docker cp telegram-claim-bot:/usr/src/app/screenshots/ screenshots/
```
> Note: The script interacts with two main entities: Telegram and the Game. On checking your screenshots you may see that the Telegram interactions are showing correctly, but that the iFrame for the game is blank. This may indicate that the game is offline, or that they are blocking Telegram Web. Enabling the built-in proxy may help the script appear to be coming from a mobile device app in the case of the second issue.

## Enable maximum verbosity:
1. This will show all the steps of the process, no matter how minor. It may give clues as to why or at what step the script is failing.
2. Open the script as if you wish to create a new game session (more advanced users can directly edit the settings in **`variables.txt`**).
3. Set the **`verboseLevel`** to 3 (maximum) and restart the scripts as above.

## Restart the stuck game session:
1. If you have not already restarted the stuck game session, use the Linux Process Manager 2 (PM2) command to restart it:
```
pm2 restart [process name]
```
2. Use PM2 logs command (**`pm2 logs`**) or the packaged status command (**`./launch.sh status`**) to monitor the process for errors as it restarts.

## Renew the stuck game session:
1. Launch the provided status monitor with the following command:
```
./launch.sh status
```
2. Delete the stuck game session according to these instructions: [STATUS.md](https://github.com/thebrumby/HotWalletClaimer/blob/main/docs/STATUS.md). Example:
```
delete HOT:Wallet1
```
3. Use **`./launch.sh`** to recreate the game session.

If none of the above works, kindly open a support ticket, including sufficient screenshots and information to allow us to help you. Support tickets that don’t show evidence of following this troubleshooting guide may just get closed without further communication from us.

The preferred language of support is English. We may choose to provide support in other languages using ChatGPT as an interpreter. However, for the benefit of all members and because the developer’s main language is English, non-English requests may be closed without further communication.

## Step 100 - QR code is showing:
If you get the error for the QR code still showing, it means that the Telegram session that you used to set up the game session has been revoked (in the mobile app, Settings --> Devices --> Terminate Session). For you to resolve this error you will need to delete the saved Telegram session, along with all games that were set up using that Telegram session, and then reauthenticate the Telegram sessions and set the games up again.

## Built-in proxy - needs to be running for Blum, Vertus, and some others!
The built-in proxy is an optional feature for most games, but when enabled, it intercepts data between the browser session and the game. If a user-agent is set and matches an iOS device, the proxy will attempt to rewrite the "tg-data" to show the platform as the iOS app (instead of a desktop browser). Similarly, for Android devices, the data will be modified to indicate it is coming from the Android app.

If the proxy is used and no user-agent is set, it defaults to mimicking an Apple iPhone. Some games, such as Blum, require the use of the proxy to connect, even if it is disabled in the user settings. In such cases, the proxy is automatically enabled for functionality.

If the proxy crashes, you may need to reset it by following these steps:

```
pm2 delete http-proxy
pm2 save
apt install lsof
# or `sudo apt install lsof` if you are on stand-alone Linux and require sudo authority
sudo lsof -i :8080
```

![image](https://github.com/user-attachments/assets/340039b3-0d28-4ede-a6ee-3e079b395148)

If a process is using port 8080, find the process ID (PID) and terminate it. For example, the PID in the above screenshot is 351071, however, you should substitute your real PID for the one in the example. You can kill the process with the following command:

```
taskkill /PID 351071 /F
# or alternatively use `kill` as below. You may also need to use sudo if prompted.  
kill -9 351071
```

After that, restart the built-in proxy:
```
./launch.sh enable-proxy
```

### Final thought:
If you're having trouble setting up the dependencies and requirements to run this script, consider using Docker Desktop (on Windows or macOS) or Docker CLI (on a VPS). The Docker setup includes everything pre-built and tested, making it much easier to get up and running.

If the troubleshooting steps here don’t resolve your issue and you can’t find the answer in previously closed issues, feel free to open a support ticket. However, please note that vague posts like "doesn't work" without any detailed information may be closed, locked, or deleted.
