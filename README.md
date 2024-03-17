# Near Protocol: Herewallet Hot Auto-Claim Bot

This Python script automates claiming HOT tokens from the HereWallet app, which operates on the NEAR Protocol. The app allows users to "mine" HOT tokens distributed on the NEAR blockchain. For maximum rewards, users must log in regularly to claim tokens. This script streamlines the process, ensuring you receive the most HOT tokens possible by automatically logging in and claiming tokens when the wallet reaches capacity. If a wallet isn't full, the script calculates the remaining time and waits before retrying, optimizing network efficiency. By using SCREEN for unattended access, you can simultaneously manage multiple accounts.

⚠️ Important: The Claim HOT game has quickly onboarded over 3.5 million users in under two months. This high demand has previously overloaded the NEAR Protocol blockchain. If you encounter script errors, consider waiting 24 hours before retrying. Updates will be pushed out to this script as needed to adapt to any structural changes in the game.

The game can be found here: https://t.me/herewalletbot/app?startapp=3441967

## 🚀 How To Use (installation based on Ubuntu 20.04 and 22.04)

### Linux Users - Quick Start
#### Install GitHub (if necessary), fetch this repository, run the install script

- VPS users should make an SSH connection via PuTTy or open the Command Window on a local machine.

   ```bash
   sudo apt install -y git || true && git clone https://github.com/thebrumby/HotWalletBot.git && cd HotWalletBot && chmod +x install.sh && ./install.sh
   ```
Start your first session with ```screen -S first_session```. Execute the Python script using ```python3 claim.py```, then follow the prompts to enter your session_ID (any unique ID of your choosing), your seed phrase, and log into Telegram. Once logged in, you should see the time until the script will attempt to claim. At this point, you may detach from the session (allowing it to run in the background) by pressing CTRL+A+D. You can later resume a running session with ```screen -r```.

If you have a second account, start another session with ```screen -S screen_session``` and execute the Python script ```python3 claim.py```. You may now log in as described above to the second account. You can exit Screen and leave the script running unattended by pressing ```CTRL+A+D```. ```screen -r``` will now list the available sessions to resume.

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

Note: You have two options to integrate your accounts:
1) Create a seed.txt file in the same directory as claim.py. This will load when claim.py starts (not recommended on shared computers).
2) Operate without a seed.txt file. You will be prompted to enter the seed phrases every time you start the script (most secure).

Each seed phrase should be 12 words, each separated by a space.
As mentioned earlier, you may enter more than one seed phrase, with each one on a separate line.

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

