# Hot Wallet Auto-Claim Bot

This Python script automates the process of claiming HOT tokens from the Herewallet app, which operates on the Near Protocol. Within the first 40 days of its release, the Mine Hot app reportedly gained 3 million users, allowing them to mine HOT tokens that are stored on the Near Blockchain. Users are required to log in every few hours to mine or claim tokens. This script simplifies the task, especially for those with multiple accounts, by cycling through 12-word seed phrases, logging into each wallet, and claiming tokens when the wallet is full. If a wallet is not ready for claiming, the script retrieves the time until it is filled and waits before trying again, reducing unnecessary network traffic.

Note: This game/app has already caused various overloads to both Near Protocol 

## 🚀 How To Use


### 1. Install Python & PIP

If Python and Python Package Installer are not installed on your Windows machine, search for the instuctions to install via the internet:

Ubuntu users: 
sudo apt update && sudo apt install -y python3 python3-pip

#### Verify Installation

- Open a new command prompt or PowerShell window. VPS users should make an SSH connect via PuTTy or similar.
- Type `python --version` or `python3 --version` and press Enter to verify the installation.

### Linux Users

#### 1. Install Google Chrome

The commands below are tested Ubuntu-based distributions. Adjust accordingly if you're using a different distribution.

wget --no-verbose -O /tmp/chrome.deb https://mirror.cs.uchicago.edu/google-chrome/pool/main/g/google-chrome-stable/google-chrome-stable_114.0.5735.198-1_amd64.deb
sudo apt install -y /tmp/chrome.deb
rm /tmp/chrome.deb

sudo apt install unzip
wget https://chromedriver.storage.googleapis.com/114.0.5735.90/chromedriver_linux64.zip
unzip chromedriver_linux64.zip
sudo mv chromedriver /usr/local/bin/
sudo chmod +x /usr/local/bin/chromedriver
chromedriver --version

# Clone this repository
git clone https://github.com/thebrumby/HotWalletBot.git

# Go into the repository
cd HotWalletBot

# Install dependencies
pip install selenium
pip install Pillow

# Run the script (comman line option)
python claim.py
python3 claim.py


# Run the script (Use screen for a Persistent Session)

If you want the script to run continuously, even after disconnecting from the server, use screen:

sudo apt install screen
Create session: screen -S hot_wallet
Check you are in the HotWalletBot directory or cd HotWalletBot
Start the script: python claim.py or python3 claim.py
Exit session and leave it running in the background CTRL+A+D
Resume session: screen -r

If you find this script useful, please consider buying me a coffee to show your support.
https://www.buymeacoffee.com/HotWallletBot

Note: You have two options to 