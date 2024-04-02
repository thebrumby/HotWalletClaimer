# Near Protocol: Herewallet Hot Auto-Claim Bot

This Python script simplifies claiming the cryptocurrency HOT, using the "HereWalletBot" app, a free-to-use application on Telegram that is also Web3 enabled on the NEAR Protocol blockchain. The app requires frequent logins to claim HOT tokens if you intend to accumulate the maximum rewards. This script automates these actions, attempting to execute the claim sequence immediately once the wallet is full. Should the wallet not be filled, it calculates the time until completion and waits to claim, optimizing network usage and lowering your Gas Fees.

💡 TIP: Claiming multiple HereWallet accounts with a single Telegram account is possible by setting up individual sessions. This can be achieved through SCREEN, as outlined below, or with alternatives like PM2, allowing for separate, dedicated sessions for each game account.

The HereWallet app/game can be found here: [https://t.me/herewalletbot/app?startapp=3441967-village-85935](https://t.me/herewalletbot/app?startapp=3441967-village-85935)

If you find this script useful, please consider buying me a coffee to show your support.
- https://www.buymeacoffee.com/HotWallletBot

## 🚀 How To Use (installation based on Ubuntu 20.04/22.04)

### Linux Users - Quick Start (or follow the manual steps below)
#### Install GitHub (if necessary), fetch this repository, run the install script!

- VPS users should make an SSH connection via PuTTy or open the Command Window on your local machine.

   ```bash
   sudo apt install -y git || true && git clone https://github.com/thebrumby/HotWalletBot.git && cd HotWalletBot && chmod +x install.sh && ./install.sh
   ```
Start your first session with ```screen -S first_session```. If you are not in the HotWalletBot directory, you must ```cd HotWalletBot```. Execute the Python script using ```python3 claim.py```, then follow the [Usage Notes](#usage-notes) to set up the session and automate the claiming process. Pressing ```CTRL+A+D``` simultaneously will leave this session running in the background. ```screen -r first_session``` will resume the session for you to check on progress, or for errors. If you wish to start the Python script without the CLI setup and go straight into an existing session, use ```python3 claim.py 1```. Note: 1 is the default session name for the first session, if you changed it,  replace "[1]"  with the exact Session Name you specified when setting this session up.

If you have a second account, from the command line (not within the first Screen), start another session with ```screen -S second_session``` and execute the Python script ```python3 claim.py```. You may now run another instance of ```python3 claim.py``` to log into the second account. You can exit Screen and leave the script unattended by pressing ```CTRL+A+D```. ```screen -r second_session``` will resume the session for you to check on progress, or for errors. If you wish to start the Python script without the CLI setup and go straight into an existing session, use ```python3 claim.py 2```. Note: 2 is the default session name for the second session, if you changed it,  replace "[2]"  with the exact Session Name you specified when setting this session up. 

💡 Tip: Each active Python script, when not idle (e.g. logging in or making a claim), requires approximately 450 MB of server memory and also utilizes a portion of CPU resources for the Chrome Driver process. It's essential to assess your server's capacity to ensure you have enough resources to support the number of concurrent sessions you wish to operate. Remember, the ```sudo reboot``` command can clear all active screen sessions, however, if the login process for Telegram and the HereWalletBot successfully completed, you can resume previous sessions by using the original sessionName when restarting the Python script.

<p align="center">
  <a href="https://www.youtube.com/watch?v=MjUquyLWPGw" title="YouTube Visual Instructions">
    <img src="https://img.youtube.com/vi/MjUquyLWPGw/0.jpg" alt="YouTube Visual Instructions">
  </a><br>
   See a walkthrough of all the steps, from server setup to installing the script, on <a href="https://www.youtube.com/watch?v=MjUquyLWPGw" title="YouTube Visual Instructions">YouTube</a>.
</p>

### Linux Manual installation - Ensure each command in the code block executes. 

1. **Install Python & PIP:**

   ```bash
   sudo apt update
   sudo apt install -y python3 python3-pip
   python3 --version   
   ```
2. **Download & Install the Chrome `.deb` package:**

   ```bash
   wget -O /tmp/chrome.deb https://mirror.cs.uchicago.edu/google-chrome/pool/main/g/google-chrome-stable/google-chrome-stable_114.0.5735.198-1_amd64.deb
   sudo apt install -y /tmp/chrome.deb
   rm /tmp/chrome.deb   
   ```
3. **Download & Install Chromedriver:**

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
7. **Start a Screen Session for Unattended Access & execute the Python script:**
   ```bash
   screen -S yourSessionName
   python3 claim.py [optionalExistingSessionName]
   ```
   - You can exit the screen session by pressing ```CTRL+A+D``` simultaneously, it will remain running in the background for unattended claims, provided you successfully log in.
   - You can resume an active screen session with ```screen -r yourSessionName```

<a name="usage-notes"></a>
## Usage Instructions

#### After executing the script with ```python3 claim.py```, the process flow is as follows:

1. **Force Claim on First Run:** Enter `y` to force a claim even if the wallet isn't full; or press `<Enter>` to skip.
2. **Enable Debugging:** Type `y` to activate debugging screenshots or press `<Enter>` to keep debugging off (default).
3. **QR Code Login Option:** Press `<Enter>` to log in by scanning a QR code, or type `n` for phone number and OTP.
4. **Session Name Configuration:**
   - Press `<Enter>` to assign a default session name of ascending numeric values (1, 2, 3, etc.).
   - Alternatively, you can enter your value (JohnDoes_Wallet, myWallet1, etc).
   - If restarting the script after stopping it, you may want to re-use a previous Session Name to keep the screenshots in the same location and to attempt to avoid logging in again on Telegram.
5. **Country Name for Telegram:**
   - Input your Country Name exactly as listed on [Telegram's login page](https://web.telegram.org/k/), like "USA" or "UNITED KINGDOM".
   - As a shortcut, pressing `<Enter>` attempts to select the corresponding Country Name based on your internet connection IP address.
   - If your IP address location differs from your registered phone number location, you MUST explicitly specify the Country Name. 
6. **Phone Number Entry:** Omit the initial "0" from your phone number when prompted.
7. **One-Time Password (OTP)**: Enter the One-Time Password that has been sent to your Telegram Messaging Account.
8. **Seed Phrase Input for HereWallet Login:** Your seed phrase remains private, with script transparency ensuring security. Ensure your phrase consists of exactly 12 words, spaced correctly without punctuation or numbers.

After following these steps, if all inputs are correctly entered, and assuming no flooding block is in place, you'll successfully logged into both Telegram and HereWallet.

## Use of PM2

PM2 is a popular process manager for Node.js applications, but it can manage processes for any type of application, including Python scripts. It's often used in production environments to ensure applications run continuously (auto-restarting after crashes or system reboots), facilitate common system admin tasks, and provide a straightforward way to manage application logging, monitoring, and clustering. While we do not intend to cover the use of PM2 as part of this project, but considering you may pass the session name as a system argument when calling the script (```python3 claim.py yourSessionName```), then it would be a logical way of managing sessions that have already been defined.

## Inspiration and Enhancement

This project was inspired by [vannszs/HotWalletBot](https://github.com/vannszs/HotWalletBot.git). However, the code in this repository has been completely rewritten and extended and is not a fork.

# Security Considerations for HotWalletClaimer Usage

The HotWalletClaimer script allows users to automate interactions with the "Claim Hot" game. 

⚠️ HTTPS Communication: All interactions with the Telegram Web App occur over HTTPS, providing a secure channel.

⚠️ Your seed phrase and Telegram login details are not stored or transmitted by this script, except during the unavoidable one-time login process on https://web.telegram.org/k/#@herewalletbot. 

⚠️ Debugging: Enabling debug mode captures the whole process as screenshots, excluding the seed phrase entry step. These images are stored locally to assist you in the event of errors and are not otherwise transmitted or uploaded in any way.

## Security Considerations:

💡 Private Devices: Only use this script on private, secure machines or Virtual Private Servers that only you can access.

💡 Caution with Seed Phrases: Be very cautious with accounts of significant value. Consider the effect of any unintended loss should your seed phrase become compromised.

💡 Awareness and Discretion: Understand the security trade-offs of using this automation tool or any other third-party tools. Your vigilance is crucial in safeguarding your information.

## Disclaimer:
Use of HotWalletClaimer is at your own risk. While we are confident that the script neither transmits nor stores your sensitive data, it is essential to acknowledge that devices can become compromised through viruses or other malicious software. The developers of HotWalletClaimer exclude any liability for potential security breaches or financial losses. It is your responsibility to safeguard your digital security. Always prioritize protecting your accounts and sensitive information.

