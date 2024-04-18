# Near Protocol: HereWallet HOT Token Claim Assistant

This Python script aids in mining (claiming) the cryptocurrency "HOT" through the "HereWalletBot", a free-to-use, Telegram-based Web3-enabled app operating on the NEAR Protocol blockchain. To maximize rewards, users need to frequently visit the app to claim tokens. The script automates this process by initiating claims immediately once the wallet is full. If the wallet isn't yet filled, it calculates the time until completion and waits for the optimal moment to claim, minimizing network load and reducing Gas Fees.

💡 **TIP:** Although you cannot register multiple wallets to a single Telegram account, this script enables you to manage multiple pre-existing HereWallet accounts with just one Telegram login by handling each account in its own separate virtual browser session. Alternatively, you can manage each wallet with its own individual Telegram login if preferred.

If you find this script useful, please consider [buying me a coffee](https://www.buymeacoffee.com/HotWallletBot) as a token of appreciation. To join the HereWallet game and further support my efforts, you can use [this link](https://t.me/herewalletbot/app?startapp=3441967-village-85935) to make me your referrer, which helps me earn extra tokens. Thank you in advance for any support!

💡 **TIP:** For straightforward unattended claim management, novice users may find [SCREEN](#screen) invaluable. Alternatively, more experienced Linux users will appreciate the additional features provided by [PM2](#pm2).

#### Windows 10 & 11 Users - Utilize WSL2 for a Seamless Experience:
For detailed instructions on setting up your environment using Windows Subsystem for Linux 2 (WSL2), please refer to our [Windows Setup](#windows) section.

<a name="quick-start"></a>
#### Quick Start Installation (based on Ubuntu 20.04/22.04):
Copy and paste the Quick Start command block into your terminal (or follow the manual steps below if you prefer).

   ```bash
   sudo apt install -y git || true && git clone https://github.com/thebrumby/HotWalletBot.git && cd HotWalletBot && chmod +x install.sh && ./install.sh
   ```
<a name="screen"></a>
## Use of ```SCREEN``` to Manage Unattended Claim Sessions (Sessions are lost after reboot)
- **Starting Your First Session:**
  - Start with `screen -S first_session`. If you are not in the HotWalletBot directory, navigate there with `cd HotWalletBot`.
  - Execute the script with `python3 claim.py` and follow the [Usage Notes](#usage-notes) to set up the session and automate the claiming process.
  - Detach from the screen session and keep it running in the background by pressing `CTRL+A+D`.
  - To resume the session and check progress or for errors, use `screen -r first_session`.
  - If you wish to start the script without the CLI setup and directly enter an existing session, use `python3 claim.py 1`. Note: "1" is the default session name for the first session; if you changed it, replace "1" with your specified session name.

- **Starting a Second Account Session:**
  - From the command line (outside the first screen session), start another session with `screen -S second_session` and execute `python3 claim.py`.
  - Detach from this second screen session by pressing `CTRL+A+D`.
  - To resume the session and check progress or for errors, use `screen -r second_session`.
  - If you wish to start the script without the CLI setup and directly enter an existing session, use `python3 claim.py 2`. Note: "2" is the default session name for the second session; if you changed it, replace "2" with your specified session name.

💡 **TIP:** Each session in wait status uses around 30mb of memory and virtually no CPU load. During the Claim or Login phases, however, each session requires approximately 450 MB of memory and utilizes a larger portion of your CPU resources. The concurrent claims setting (default 1) helps limit the number of active claims to prevent hardware overload. Assess your hardware's capacity to determine how many simultaneous sessions it can handle, and adjust the maximum number accordingly by following the [Usage Notes](#usage-notes). Even with a maximum of one allowed claim session, claiming on multiple wallets is possible; additional claims will queue until a session slot becomes available.

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

<a name="pm2"></a>
## Use of ```PM2``` to Execute Unattended Claim Sessions (Persist After Reboot)

- **Installation:**
  - Install PM2 manually, or use the install script packaged in the HotWalletBot directory. Navigate to the HotWalletBot directory if not already there:
    ```bash
    sudo chmod +x install_pm2.sh && sudo ./install_pm2.sh
    ```

- **Setup Before Using PM2:**
  - Open the script using `python3 claim.py` and complete the setup for each wallet. Follow the process to log into Telegram and enter your seed phrase. After setup, you will be prompted whether to exit before moving on to the claim function. Choose 'n' to exit the script and resume the session with PM2.

- **Initialize PM2 with Systemd (Linux/Ubuntu):**
  - Ensure that PM2 starts on boot:
    ```bash
    pm2 startup systemd
    ```
    Follow the on-screen prompt to execute the suggested command if you are not superuser.

- **Adding Sessions to PM2:**
  - To add a Python script as a PM2 session, use the command below. This example starts a session named `firstWallet` which loads a previously saved `claim.py` session named `1`:
    ```bash
    pm2 start claim.py --name firstWallet -- 1
    ```
    Note: Replace `1` with the actual Session name you set during setup if different.

  - To add a second session named `secondWallet`:
    ```bash
    pm2 start claim.py --name secondWallet -- 2
    ```
    Note: Replace `2` with the actual Session name.

- **Manage PM2 Sessions:**
  - Save configuration to persist through reboots:
    ```bash
    pm2 save
    ```
  - View all PM2 managed processes:
    ```bash
    pm2 list
    ```
  - View logs for a specific session (e.g., `firstWallet`):
    ```bash
    pm2 log firstWallet
    ```
  - To remove a managed wallet:
    ```bash
    pm2 delete firstWallet
    ```
  - To stop PM2 from starting on boot:
    ```bash
    pm2 unstartup systemd
    ```
 
<p align="center">
  <a href="https://www.youtube.com/watch?v=JUmczcdsaAw" title="YouTube PM2 Instructions">
    <img src="https://img.youtube.com/vi/JUmczcdsaAw/0.jpg" alt="YouTube PM2 Instructions">
  </a><br>
   See a walkthrough of how to automate claims using PM, on <a href="https://www.youtube.com/watch?v=JUmczcdsaAw" title="YouTube Visual Instructions">YouTube</a>.
</p>

<a name="windows"></a>
## Guide for Setting Up WSL2 in a Windows 10/11 Environment

Windows Subsystem for Linux (WSL2) allows you to run a GNU/Linux environment directly on Windows, unmodified, without the overhead of a traditional virtual machine or dualboot setup. This makes it an excellent choice for running this script in a Linux-like environment on Windows machines, as the commands and drivers detailed below can be utilized directly. Alternatively, watch the video below and consider using a cloud-based Linux server (12-month free trials are often available).

### Step 1: Enable WSL2 and Install Ubuntu 22.04

1. **Open the Microsoft Store:**
   - Click the Start menu and open the Microsoft Store. Search for "Ubuntu 22.04 LTS" and click on the install button. This will download and install the Ubuntu terminal environment.

2. **Enable Windows Subsystem for Linux (WSL):**
   - Before you can use Ubuntu, ensure that WSL is enabled and set up to use the newer WSL2 version. Open PowerShell as an administrator and run the following commands:

     ```bash
     dism.exe /online /enable-feature /featurename:Microsoft-Windows-Subsystem-Linux /all /norestart
     ```

     This command enables the WSL feature. Restart your computer after this step to ensure changes take effect.

3. **Set WSL2 as Your Default Version:**
   - After your system restarts, open PowerShell again as an administrator and set WSL2 as the default version with this command:

     ```bash
     wsl --set-default-version 2
     ```

     If this is your first time setting up WSL, you might be prompted to update the WSL2 kernel. Follow the link provided in the PowerShell window to download and install the WSL2 kernel update package.

### Step 2: Launch Ubuntu 22.04

1. **Start Ubuntu 22.04:**
   - After installation, you can start Ubuntu by searching for "Ubuntu 22.04" in the Start menu and clicking on the app icon. The first launch will take a few minutes as it finalizes the setup.

2. **Create a User Account and Password:**
   - Upon first launch, you'll be prompted to enter a new username and password. This account will be your default user for Ubuntu and will have sudo (administrative) privileges.

### Step 3: Update and Upgrade Ubuntu (Optional but Recommended)

1. **Update Your System:**
   - It's a good practice to update your package lists and upgrade the packages right after installation. In the Ubuntu terminal, run:

     ```bash
     sudo apt update && sudo apt upgrade
     ```

     This will ensure all your software is up to date.

### Step 4: Follow the Setup and Initialization as per the Ubuntu/Linux Instructions

- Now that you have Ubuntu set up, you can return to the [Quick Start](#quick-start) section at the top of the page for further instructions.

### Step 5: Configure WSL & PM2 to Start When Your Machine Starts (Optional)

- Press `Win + R` to open the Run dialog box. Type `shell:startup` to open the Startup folder. Then, copy the `windows_pm2_restart.bat` file from your HotWalletBot directory into the Startup folder.

<p align="center">
  <a href="https://www.youtube.com/watch?v=2MCemn70ysI" title="Setting up Ubuntu within Windows using WSL.">
    <img src="https://img.youtube.com/vi/2MCemn70ysI/0.jpg" alt="Setting up Ubuntu within Windows using WSL.">
  </a><br>
   See a walkthrough of how to setup Ubuntu within Windows using WSL with our <a href="https://www.youtube.com/watch?v=2MCemn70ysI" title="YouTube Visual Instructions">YouTube</a>.
</p>

<a name="usage-notes"></a>
## V1.4.2 Release Notes - Improved Claim Handling & Configurable Settings

### Usage Instructions
After executing the script with `python3 claim.py`, you will be prompted to update settings and configure the session:

1. **Update Settings:**
   - Decide if you want to update script parameters. If you choose "y", you'll be prompted review/update the following:
      - `forceClaim`: Force a claim the first time the script runs, even if the wallet isn't full, or wait until full.
      - `debugIsOn`: Activate debugging to save screenshots to your filesystem; default is off.
      - `hideSensitiveInput`: Hide sensitive input such as phone numbers and seed phrases; default is ON.
      - `screenshotQRCode`: Log in by QR code; default is true, the alternative is by phone number and OTP.
      - `maxSessions`: Defines the number of simultaneous claim sessions permitted. Even if only one session is allowed at a time, you can manage multiple wallets. Additional wallets will queue and wait for an available claim session slot.
      - `verboseLevel`: Control verbosity of console messages; ranges from 1 (minimal), 2 (main steps) 3 (all messages).
      - `forceNewSession`: Overwrite an existing session and force a new login. Requires repeating both Telegram log-in & seed words entry - useful if an existing session has errors.
2. **Session Name Configuration:**
   - Auto-assigns a numeric value or accepts a custom session name. Reusing a name will attempt to resume that session.
3. **Login Options:**
   - The default is using scanning a QR Code screenshot. If that doesn't work, or you choose otherwise, follow the OTP login method in steps 4. & 5.
4. **Country Name and Phone Number for Telegram:**
   - Enter your Country Name as it appears on Telegram's login page or use the default based on your IP address.
5. **One-Time Password (OTP):**
   - Input the OTP sent to your Telegram account.
6. **Two-Factor Authentication (2FA):**
   - If your Telegram account has 2FA enabled, you'll be prompted to enter your password after scanning the QR code or entering the OTP. Input your 2FA password to continue the login process.
7. **Seed Phrase Input for HereWallet Login:**
   - Enter your 12-word seed phrase, ensuring it is spaced correctly without punctuation or numbers.
8. **Exit & resume later (possibly in PM2) or Continue in the CLI script:**
   - Choose to exit the script and save progress for later or continue to the claim function.

Remember to check and adjust your settings upon startup to optimize the script's performance to your server's capabilities.

After following these steps, if all inputs are correctly entered, and assuming no flooding block is in place, you'll successfully logged into both Telegram and HereWallet.

### Linux Manual installation - Ensure each command in the code block executes. 

1. **Install Python, Zbar & PIP:**

   ```bash
   sudo apt update
   sudo apt install -y python3 python3-pip
   sudo apt-get install -y libzbar0
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
   pip install selenium Pillow pyzbar qrcode-terminal
   ```

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

