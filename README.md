# Near Protocol: Herewallet Hot Auto-Claim Bot

This Python script simplifies claiming the cryptocurrency HOT, using the "HereWalletBot" app, a free-to-use application on Telegram that is also Web3 enabled on the NEAR Protocol blockchain. The app requires frequent logins to claim HOT tokens if you intend to accumulate the maximum rewards. This script automates the claim process, attempting to claim immediately after the wallet is full. Should the wallet not be filled, it calculates the time until completion and waits to claim, optimizing network usage and lowering your Gas Fees.

💡 TIP: It is possible to manage multiple HereWallet accounts using just one Telegram account by initiating several individual sessions. For a straightforward setup, consider using **SCREEN** (see the quick start guide below). However, for the more confident user, [PM2](#pm2) is recommended.

If you find this script useful, please consider [buying me a coffee](https://www.buymeacoffee.com/HotWallletBot). The HereWallet game can be found [HERE](https://t.me/herewalletbot/app?startapp=3441967-village-85935).

#### Windows Users - Utilize WSL2 for a Seamless Experience:
Windows Subsystem for Linux (WSL2) allows you to run a GNU/Linux environment directly on Windows, unmodified, without the overhead of a traditional virtual machine or dualboot setup. This makes it an excellent choice for running this script in a Linux-like environment on Windows machines, as the commands and drivers detailed below can be utilized directly. Alternatively, watch the video below and consider using a cloud-based Linux server (12-month free trials are often available).

#### Linux Users - Quick Start (based on Ubuntu 20.04/22.04):
Copy and paste the Quick Start command block into your terminal (or follow the manual steps below if you prefer).

- VPS users should make an SSH connection via PuTTy or open the Command Window on your local machine.

   ```bash
   sudo apt install -y git || true && git clone https://github.com/thebrumby/HotWalletBot.git && cd HotWalletBot && chmod +x install.sh && ./install.sh
   ```
Start your first session with ```screen -S first_session```. If you are not in the HotWalletBot directory, you must ```cd HotWalletBot```. Execute the Python script using ```python3 claim.py```, then follow the [Usage Notes](#usage-notes) to set up the session and automate the claiming process. Pressing ```CTRL+A+D``` simultaneously will leave this session running in the background. ```screen -r first_session``` will resume the session for you to check on progress, or for errors. If you wish to start the Python script without the CLI setup and go straight into an existing session, use ```python3 claim.py 1```. Note: 1 is the default session name for the first session, if you changed it,  replace "[1]"  with the exact Session Name you specified when setting this session up.

If you have a second account, from the command line (not within the first Screen), start another session with ```screen -S second_session``` and execute the Python script ```python3 claim.py```. You may now run another instance of ```python3 claim.py``` to log into the second account. You can exit Screen and leave the script unattended by pressing ```CTRL+A+D```. ```screen -r second_session``` will resume the session for you to check on progress, or for errors. If you wish to start the Python script without the CLI setup and go straight into an existing session, use ```python3 claim.py 2```. Note: 2 is the default session name for the second session, if you changed it,  replace "[2]"  with the exact Session Name you specified when setting this session up. 

💡 Tip: Each active Python script, requires approximately 450 MB of server memory and also utilizes a portion of CPU resources for the Chrome Driver process while logging in or making a claim. It is important to assess your server's resources to ensure you can support the number of concurrent sessions you wish to operate.

<p align="center">
  <table style="margin-left: auto; margin-right: auto; width: 100%;"><tr>
    <td style="width: 50%; vertical-align: top;">
      <a href="https://www.youtube.com/watch?v=MjUquyLWPGw" title="YouTube Visual Instructions">
        <img src="https://img.youtube.com/vi/MjUquyLWPGw/0.jpg" alt="YouTube Visual Instructions" style="max-width: 100%; height: auto;">
      </a>
      <div style="text-align: center; margin-top: 10px;">
        See a walkthrough of all the steps, from server setup to installing the script, on <a href="https://www.youtube.com/watch?v=MjUquyLWPGw" title="YouTube Visual Instructions">YouTube</a>.
      </div>
    </td>
    <td style="width: 50%; vertical-align: top;">
      <img src="https://github.com/thebrumby/HotWalletClaimer/assets/29182343/f3c2f57c-282a-4d3c-be9a-15113a466c44" alt="image" style="max-width: 100%; height: auto;">
    </td>
  </tr></table>
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
   sudo apt install -y wget
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
   python3 claim.py [optionalSessionName]
   ```
   - You can exit the screen session by pressing ```CTRL+A+D``` simultaneously, it will remain running in the background for unattended claims, provided you successfully log in.
   - You can resume an active screen session with ```screen -r yourSessionName```
   - By specifying an [optionalSessionName], it will attempt to resume that session (if it exists) or set it up without the option to change the default settings in the command line interface. 

<a name="usage-notes"></a>
## V1.4.1 Release Notes - Improved Claim Handling & Configurable Settings

### Usage Instructions
After executing the script with `python3 claim.py`, you will be prompted to update settings and configure the session:

1. **Update Settings:**
   - Decide if you want to update script parameters. If you choose "yes", you'll be prompted review/update the following:
      - `forceClaim`: Force a claim even if the wallet isn't full; default is to wait until full.
      - `debugIsOn`: Activate debugging to save screenshots; default is off.
      - `hideSensitiveInput`: Hide sensitive input such as phone numbers and seed phrases; default is ON (True).
      - `screenshotQRCode`: Log in by QR code; default is true, alternative is phone number and OTP.
      - `maxSessions`: Number of simultaneous claim sessions; affects memory and CPU usage.
      - `verboseLevel`: Control verbosity of console messages; ranges from 1 (minimal) to 3 (all messages).
      - `forceNewSession`: Overwrite existing session and force a new login; useful if an existing session has errors.
2. **Session Name Configuration:**
   - Auto-assigns a numeric value or accepts a custom session name. Reusing a name will attempt to resume that session.
3. **Login Options:**
   - The default is using scanning a QR Code screenshot. If that doesn't work, or you choose otherwise, follow the OTP login method in steps 4. & 5.
4. **Country Name and Phone Number for Telegram:**
   - Enter your Country Name as it appears on Telegram's login page or use the default based on your IP address.
5. **One-Time Password (OTP):**
   - Input the OTP sent to your Telegram account.
6. **Seed Phrase Input for HereWallet Login:**
   - Enter your 12-word seed phrase, ensuring it is spaced correctly without punctuation or numbers.
7. **Exit & resume later (possibly in PM2) or Continue in the CLI script:**
   - Choose to exit the script and save progress for later or continue to the claim function.

Remember to check and adjust your settings upon startup to optimize the script's performance to your server's capabilities.


After following these steps, if all inputs are correctly entered, and assuming no flooding block is in place, you'll successfully logged into both Telegram and HereWallet.

<a name="pm2"></a>
## Use of PM2

Install PM2 manually, or use the install script packaged here:

   ```bash
   sudo chmod +x install_pm2.sh && sudo ./install_pm2.sh
   ```

Before using PM2 to manage your wallet sessions, you should open the script with ```python3 claim.py``` and set up each wallet. After following the process to sign into Telegram and enter your seed phrase, you will be prompted if you want to exit before being handed over to the claim function. You can select 'n' to exit the script and resume the session with PM2 as outlined below. 

- First, initialize PM2 with systemd to ensure your applications start on boot:
   - ```pm2 startup systemd``` (follow the on-screen prompt to enable resume on reboot if you are not superuser)
- Use the following command to add your Python script as a PM2 session. This example adds a session named firstWallet:
   - ```pm2 start claim.py --name firstWallet -- 1``` (if you named your session folder something else during setup, replace 1 with your session name)
- To add a second session, you can use a similar command with a different name and session identifier:
   - ```pm2 start claim.py --name secondWallet -- 2``` (if you named your session folder something else during setup, replace 2 with your session name)
- After adding/updating your sessions, save them with the command below. This makes sure your session configuration persists through system reboots:
   - ```pm2 save```
- To view the current list of processes managed by PM2:
   - ```pm2 list```
- To see the output which would have been previously visible in the Screen console:
   - ```pm2 log firstWallet```
- If you need to remove a wallet from PM2's management, you can delete it by its name:
   - ```pm2 delete firstWallet```
- If you wish to stop using PM2 as a service, you can disable it with:
   - ```pm2 unstartup systemd```
 
<p align="center">
  <a href="https://www.youtube.com/watch?v=JUmczcdsaAw" title="YouTube PM2 Instructions">
    <img src="https://img.youtube.com/vi/JUmczcdsaAw/0.jpg" alt="YouTube PM2 Instructions">
  </a><br>
   See a walkthrough of how to automate claims using PM, on <a href="https://www.youtube.com/watch?v=JUmczcdsaAw" title="YouTube Visual Instructions">YouTube</a>.
</p>

## Inspiration and Enhancement

The idea of using Selenium to interact with the HereWalletBot was inspired by the project [vannszs/HotWalletBot](https://github.com/vannszs/HotWalletBot.git). However, the code in this repository has been completely rewritten, with many additional features, so I do not consider it a fork. However, Kudos to the original project for the concept. 

# Security Considerations for HotWalletClaimer Usage

💡 Communication: The only external communication is with the Telegram Web App, which occurs over HTTPS, providing a secure channel.

⚠️ Your seed phrase and Telegram login details are not stored or transmitted by this script, except during the unavoidable one-time login process with https://web.telegram.org/k/#@herewalletbot. As of version v1.3.4, the Google Chrome session is now saved into the ```./HotWalletBot/selenium``` folder and in v.1.3.6 there is also a duplicate of the session in ```./HotWalletBot/backups``` - if this information was compromised, it would allow a suitably experienced individual to access your account.  

💡 Debugging: Enabling debug mode captures the whole process as screenshots, excluding the seed phrase entry step. These images are stored locally to assist you in the event of errors and are not otherwise transmitted or uploaded in any way.

## Security Best Practice:

💡 Private Devices: Only use this script on private, secure machines or Virtual Private Servers that only you can access.

⚠️ Caution with Seed Phrases: Be very cautious with accounts of significant value. Consider the effect of any unintended loss should your seed phrase become compromised.

💡 Awareness and Discretion: Understand the security trade-offs of using this automation tool or any other third-party tools. Your vigilance is crucial in safeguarding your information.

## Disclaimer:
Use of HotWalletClaimer is at your own risk. While we are confident that the script neither transmits nor stores your sensitive data, it is essential to acknowledge that devices can become compromised through viruses or other malicious software. The developers of HotWalletClaimer exclude any liability for potential security breaches or financial losses. It is your responsibility to safeguard your digital security. Always prioritize protecting your accounts and sensitive information.

