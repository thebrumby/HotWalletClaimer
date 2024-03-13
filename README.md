# Near Protocol: Hot Wallet Auto-Claim Bot

This Python script automates the process of claiming HOT tokens from the Herewallet app, which operates on the Near Protocol. It allows users to mine HOT tokens that are stored on the Near Blockchain. Users are required to log in every few hours to mine or claim tokens. This script simplifies the task, especially for those with multiple accounts, by cycling through 12-word seed phrases, logging into each wallet, and claiming tokens when the wallet is full. If a wallet is not ready for claiming, the script retrieves the time until it is filled and waits before trying again, reducing unnecessary network traffic.

Note: The Claim HOT game has already caused various overloads to both Near Protocol and strain on their Content Distribution Network (CDN).
If the system throws a lot of errors, you may need to leave it some time for the Claim HOT developers to resolve their issues before trying again.
I will attempt to keep this repository updated should the game creators update their code.

The game can be found here: https://t.me/herewalletbot/app?startapp=3441967

## 🚀 How To Use

### Linux Users - This guide is based on installation on an Ubuntu VPS server

1. **If required, install Python & PIP:**

- Open a new command prompt window. 
- VPS users should make an SSH connection via PuTTy or similar.

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
	sudo apt install unzip
	wget https://chromedriver.storage.googleapis.com/114.0.5735.90/chromedriver_linux64.zip
	unzip chromedriver_linux64.zip
	sudo mv chromedriver /usr/local/bin/
	sudo chmod +x /usr/local/bin/chromedriver
	chromedriver --version
	```

4. **Clone this repository:**

   ```bash
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


# How to leave the script running for unattended claims

If you want the script to run continuously, even after disconnecting from the server, use screen:

- Install screen if required: ```sudo apt install screen```
- Create session: ```screen -S hot_wallet```
- Check you are in the HotWalletBot directory or ```cd HotWalletBot```
- Start the script: ```python3 claim.py``` or ```python claim.py```
- To exit the session and leave it running in the background CTRL+A+D
- To later resume session: ```screen -r```

If you find this script useful, please consider buying me a coffee to show your support.
- https://www.buymeacoffee.com/HotWallletBot

Note: You have two options to integrate your accounts:
1) Create a seed.txt file in the same directory as claim.py
2) Run claim.py and you will be prompted to enter the seed phrase. It will check you entered 12 words and create seeds.txt

Each seed phrase should be 12 words, each separated by a space.
As mentioned earlier, you may enter more than one seed phrase, with each one on a separate line.

Inspired by https://github.com/vannszs/HotWalletBot.git

⚠️ Warning: While this Python script is openly available on GitHub, transparent in its code, and devoid of any malicious intent, it's crucial to understand its potential risks. The debugging function of this script generates screenshots of your login stages directly on your local machine and stores your seed phrases, unencrypted, in a text file named seeds.txt.

⚠️ Risk Assessment:

Local Machine Usage: Given that the script operates locally, there's minimal risk associated with its usage on a personal machine not accessible by others.
Seed Phrase Storage: Storing sensitive information, such as seed phrases, in an unencrypted text file poses a significant security concern.
Account Vulnerability: Accounts with high monetary value should not be used with this script due to the inherent security risks involved.
💡 Recommendations:

Privacy Concerns: Avoid installing this script on a machine accessible by others, especially in shared or public environments.
Sensitive Information: Refrain from entering seed phrases associated with accounts holding significant monetary value.
Usage Context: This script is primarily intended for use in scenarios where security is less critical, such as experimenting with the "Claim Hot" game.
⚠️ Disclaimer: The developers of this script do not assume responsibility for any misuse or unauthorized access to sensitive information. Users are advised to exercise caution and discretion when utilizing this tool.

By understanding the risks and exercising appropriate caution, users can maximize the benefits of this script while minimizing potential security vulnerabilities. Remember, your security is paramount. Stay vigilant and informed!


