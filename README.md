# Near Protocol: Herewallet Hot Auto-Claim Bot

This Python script automates claiming HOT tokens from the HereWallet app, which operates on the NEAR Protocol. The app allows users to "mine" HOT tokens distributed on the NEAR blockchain. For maximum rewards, users must log in regularly to claim tokens. This script streamlines the process, ensuring you receive the most HOT tokens possible by automatically logging in and claiming tokens when the wallet reaches capacity. If a wallet isn't full, the script calculates the remaining time and waits before retrying, optimizing network efficiency and reducing your Gas Fees!

💡 TIP: You can claim on multiple HereWallet accounts using a single Telegram account, provided you use an individual session in SCREEN as described below. However, if you attempt to log into a single Telegram account more than 20 times in 24 hours via the One-Time Password (OTP) method, you will be blocked from doing so for one day due to flooding.

The HereWallet app/game can be found here: https://t.me/herewalletbot/app?startapp=3441967

## 🚀 How To Use (installation based on Ubuntu 20.04 and 22.04)

### Linux Users - Quick Start
#### Install GitHub (if necessary), fetch this repository, run the install script

- VPS users should make an SSH connection via PuTTy or open the Command Window on a local machine.

   ```bash
   sudo apt install -y git || true && git clone https://github.com/thebrumby/HotWalletBot.git && cd HotWalletBot && chmod +x install.sh && ./install.sh
   ```
Start your first session with ```screen -S first_session```. If you are not in the HotWalletBot directory, you must ```cd HotWalletBot```. Execute the Python script using ```python3 claim.py```, then follow the [Usage Notes](#usage-notes) below to set up the session and automate the claiming process. Pressing CTRL+A+D simultaneously will leave this session running in the background. ```screen -r``` will resume the session if you only have one active session. 

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

1) Each time you run python3 claim.py, you will be asked for a session name. If you only intend to operate one session, you can just hit enter, and it will call the session "1". If you intend to have more than one session, please give each one a unique session name. This can be "1", "2", "3", etc., or some familiar name of your choosing. The session name will be used to generate a folder in screenshots (in case debugging is enabled) and also in the Selenium folder for your browser session.
2) You will next be asked for your seed phrase. This is needed to log into the HereWallet App. The code is pretty transparent, and it does not store or transmit your seed phrase. If you enable debugging, a screenshot of your seed phrase will be saved on your local computer. The seed phrase must be exactly 12 words, with no numbers or punctuation, and each word separated by a space.
3) After entering the seed phrase, the screen will be cleared for added privacy.
4) To log into Telegram, you will be asked for your Country Code. This should be in word format and exactly match the spelling at https://web.telegram.org/k/ (log in by phone number). Examples are "USA" and "UNITED KINGDOM".
5) Next, you will be asked for your registered phone number for Telegram. This will allow them to send you a One-Time Passcode (OTP) via the Telegram Messaging App.
6) Finally, if you correctly enter the One-Time Password, and assuming you are not blocked due to flooding requests, etc., the script will now be automated, with some key steps displayed in the console.
7) If you wish to force the script to claim on the first attempt, whether the wallet is full or not, you can set forceClaim = True. If you are not getting the expected results, you can attempt to trace the problem by setting debug_is_on = True.

# How to leave the script running for unattended claims

If you want the script to run continuously, even after disconnecting from the server, use screen:

- Install screen if required: ```sudo apt install -y screen```
- Create session: ```screen -S hot_wallet```
- Check you are in the HotWalletBot directory or ```cd HotWalletBot```
- Start the script: ```python3 claim.py``` or ```python claim.py```
- To exit the session and leave it running in the background CTRL+A+D
- To later resume session: ```screen -r```

If you find this script useful, please consider buying me a coffee to show your support.
- https://www.buymeacoffee.com/HotWallletBot

Inspired by https://github.com/vannszs/HotWalletBot.git

# Security Considerations for this HotWalletBot Usage

The HotWalletBot allows users to automate interactions with the "Claim Hot" game. This tool offers the option to enter your seed phrases each time, or the convenience of storing your seed phrases through a seeds.txt file. 

⚠️ HTTPS Communication: All interactions with the web server occur over HTTPS, providing a secure channel.

⚠️ Debugging and Screenshots: Enabling debug mode captures the login process, including seed phrase entry, in screenshots. These images are stored locally, raising privacy concerns despite not directly exposing data online.

⚠️ Seed Phrases Storage: For ease of use, seed phrases can be stored in a seeds.txt file. This method, while convenient, is not secure as the information is stored unencrypted. Alternatively, you can enter the seed phrases each time you start the script. 

## Security Considerations:

⚠️ Personal Use: Ideally, use this script on a personal machine that others do not have access to. Shared or public computers significantly increase the risk of sensitive information being compromised.

⚠️ Value at Risk: We strongly advise against using this script with accounts that hold substantial monetary value due to the security risks involved.

## Recommendations:

💡 Private Devices: Preferably, only use this script on private, secure machines.

💡 Caution with Seed Phrases: Be very cautious with accounts of significant value. Consider the security implications of storing and using seed phrases with this tool.

💡 Awareness and Discretion: Understand the security trade-offs involved in using this automation tool. Your vigilance is crucial in safeguarding your information.

## Disclaimer:
The use of HotWalletBot is at your own risk. The developers are not liable for any potential security breaches or financial losses. Your digital security is your responsibility. Always prioritize the protection of your accounts and sensitive information.

This notice aims to balance the script's benefits with an awareness of its security limitations. User discretion is advised.

