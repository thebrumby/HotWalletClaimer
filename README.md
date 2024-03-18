# Near Protocol: Herewallet Hot Auto-Claim Bot

This Python script simplifies claiming HOT tokens via the HereWalletBot, a free-to-use application on Telegram that operates on the NEAR Protocol blockchain. For optimal rewards, the app requires frequent logins to claim tokens. This script automates these actions, guaranteeing the maximum accumulation of HOT tokens by executing the claim sequence once the wallet is full. Should the wallet not be filled, it estimates the time until completion and waits to claim, thus optimizing both network usage and lowering your Gas Fees.

💡 TIP: You can claim on multiple HereWallet accounts using a single Telegram account, provided you use individual sessions in SCREEN as described below. Each time you start ```claim.py```, and enter a One-Time Password (OTP), it counts as one login attempt. Attempting to log into a single Telegram account more than 20 times in 24 hours is considered "flooding" by Telegram, and they will apply a 24-hour cooldown on further login attempts. However, once logged in, you will stay logged in unless you exit the script.

The HereWallet app/game can be found here: https://t.me/herewalletbot/app?startapp=3441967

If you find this script useful, please consider buying me a coffee to show your support.
- https://www.buymeacoffee.com/HotWallletBot

## 🚀 How To Use (installation based on Ubuntu 20.04 and 22.04)

### Linux Users - Quick Start (or follow the manual steps below)
#### Install GitHub (if necessary), fetch this repository, run the install script

- VPS users should make an SSH connection via PuTTy or open the Command Window on a local machine.

   ```bash
   sudo apt install -y git || true && git clone https://github.com/thebrumby/HotWalletBot.git && cd HotWalletBot && chmod +x install.sh && ./install.sh
   ```
Start your first session with ```screen -S first_session```. If you are not in the HotWalletBot directory, you must ```cd HotWalletBot```. Execute the Python script using ```python3 claim.py```, then follow the [Usage Notes](#usage-notes) below to set up the session and automate the claiming process. Pressing ```CTRL+A+D``` simultaneously will leave this session running in the background. ```screen -r``` will resume the session if you only have one active session. 

If you have a second account, from the command line (not within the first Screen), start another session with ```screen -S second_session``` and execute the Python script ```python3 claim.py```. You may now log in as described above to the second account. You can exit Screen and leave the script unattended by pressing ```CTRL+A+D```. ```screen -r``` will now list the available sessions to resume. You may continue to add more accounts to be claimed, provided each has a unique Screen session name and a unique Session Name when running ```python3 claim.py```.

### Linux Manual installation - Ensure each command in the code block executes. 

1. **Install Python & PIP:**

   ```bash
   sudo apt update
   sudo apt install -y python3 python3-pip
   python3 --version   
   ```
2. **Download the Chrome `.deb` package:**

   ```bash
   wget -O /tmp/chrome.deb https://mirror.cs.uchicago.edu/google-chrome/pool/main/g/google-chrome-stable/google-chrome-stable_114.0.5735.198-1_amd64.deb
   sudo apt install -y /tmp/chrome.deb
   rm /tmp/chrome.deb   
   ```
3. **Download Chromedriver:**

   ```bash
   sudo apt install -y unzip
   wget https://chromedriver.storage.googleapis.com/114.0.5735.90/chromedriver_linux64.zip
   unzip chromedriver_linux64.zip
   rm chromedriver_linux64.zip
   sudo mv chromedriver /usr/local/bin/
   sudo chmod +x /usr/local/bin/chromedriver
   chromedriver --version   
   ```
4. **Clone this repository:**

   ```bash
   sudo apt install -y git
   git clone https://github.com/thebrumby/HotWalletBot.git   
   ```
5. **Switch to the repository directory:**
   ```bash
   cd HotWalletBot   
   ```
6. **Install the dependencies:**
   ```bash
   pip install selenium Pillow   
   ```
7. **Run the Python script or use the unattended method below:**
   ```bash
   python3 claim.py   
   ```
<a name="usage-notes"></a>
# Usage Notes:

1) When you run python3 claim.py, the script will ask for a session name. For managing a single session, pressing enter will default the session to "1". If you want to claim on more than one account simultaneously, it's important to assign each a different Session Name. You might use a simple sequence like "1", "2", "3", or opt for specific identifiers such as "myWallet1", "myWallet2", and so forth. This unique name is needed to organize screenshots (if debugging is enabled) and segregate browser session data within Selenium. Not using unique names for concurrent accounts would log you out of your other sessions!
2) Next, you'll be prompted to enter your seed phrase to link access with the HereWallet App. Rest assured, the script's code is completely transparent and your seed phrase is neither stored locally nor transmitted externally. However, if you activate debugging, be aware that a series of screenshots, including one of your seed phrase, will be saved on your local device. For a successful login, ensure your seed phrase consists of exactly 12 words, with no numbers or punctuation, and each word is separated by a single space.
3) After entering the seed phrase, the screen will be cleared for added privacy.
4) To access Telegram, the script prompts for your Country name, which should be entered as text, exactly as it appears at https://web.telegram.org/k/ (log in by phone number). Examples include "USA" and "UNITED KINGDOM." If you're confident that your server's IP address aligns with the location of your phone number, simply pressing enter will prompt Telegram to use the default country code based on your server's IP address. However, if you encounter errors, or if your IP address doesn't match the country of your phone number, it will be necessary to specify your phone number's country as text.
5) Next, you will be asked for your registered phone number for Telegram. This will allow them to send you a One-Time Passcode (OTP) via the Telegram Messaging App. The standard protocol is to omit the initial "0" as it will start with the international dialing code.
6) Finally, if you correctly enter the One-Time Password, and assuming you are not blocked due to flooding requests, etc., the script will now be automated, with some of the main steps displayed in the console to reassure you it's working!
- If you wish to force the script to claim on the first attempt, regardless of whether the wallet is full or not, or if the wallet is over 25% full and eligible for claiming, you can set ```forceClaim = True```.
- If you are not getting the expected results, you can attempt to trace the problem by setting ```debug_is_on = True```.

# How to leave the script running for unattended claims

If you want the script to run continuously, even after disconnecting from the server, use SCREEN:

- Install screen if required: ```sudo apt install -y screen```
- Create session: ```screen -S hot_wallet```
- Check you are in the HotWalletBot directory or ```cd HotWalletBot```
- Start the script: ```python3 claim.py``` or ```python claim.py```
- To exit the session and leave it running in the background CTRL+A+D
- To later resume session: ```screen -r```

Inspired by a similar project: https://github.com/vannszs/HotWalletBot.git

# Security Considerations for HotWalletClaimer Usage

The HotWalletClaimer script allows users to automate interactions with the "Claim Hot" game. 

⚠️ HTTPS Communication: All interactions with the Telegram Web App occur over HTTPS, providing a secure channel.

⚠️ Your seed phrase and Telegram login details are not saved on your local machine or transmitted unless you enable debugging mode (see below). 

⚠️ Debugging and Screenshots: Enabling debug mode captures the whole claim process, including Telegram login and seed phrase entry, in screenshots. These images are stored locally, raising privacy concerns on shared computers, despite not directly exposing data online. 

## Security Considerations:

⚠️ Personal Use: For optimal security, it is recommended to use this script on a personal machine that is not accessible by others. Shared or public computers significantly increase the risk of sensitive information, such as seed phrases or login credentials, being compromised.

⚠️ Value at Risk: We strongly recommend exercising caution when using this script with accounts holding significant monetary value in Near coins or other tokens. Although the script itself should not pose any security risks, the involvement of third-party or unknown malicious code could potentially compromise the security of your funds.

## Recommendations:

💡 Private Devices: Only use this script on private, secure machines or Virtual Private Servers that only you have access to.

💡 Caution with Seed Phrases: Be very cautious with accounts of significant value. Consider the security implications of entering seed phrases with this tool; and the effect of any unintended loss.

💡 Awareness and Discretion: Understand the security trade-offs involved in using this automation tool. Your vigilance is crucial in safeguarding your information.

## Disclaimer:
Usage of HotWalletClamier is at your own risk. The developers are not liable for any potential security breaches or financial losses. Your digital security is your responsibility. Always prioritize the protection of your accounts and sensitive information.

