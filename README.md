# Telegram Claim Assistant - Mine HOT & More!

Many popular Telegram apps demand frequent logins to optimize rewards. This Python script runs on your local computer or VPS and streamlines the claim process by monitoring your account status within the app and claiming rewards at the most opportune moments. When correctly configured, the script is fully automated and features an optional random timer offset to emulate human behavior.

Take, for instance, the cryptocurrency "HOT," available on the Near Protocol. Mining happens through the "@HereWalletBot" - a Telegram-based, Web3-enabled app operating on the NEAR Protocol blockchain. Maximizing rewards entails regular visits to claim tokens. The script tracks the time until the storage pot fills, initiating a claim when full. Alternatively, it calculates the time until completion if the storage remains unfilled. It then waits for the optimal moment—adjusted by your preferred random offset—to claim, thereby minimizing network load and reducing gas fees.

We aim to expand this script to include other projects suggested by our users in the coming weeks and months. However, we do not endorse any projects, some of which may have little to no real-world value and may try to upsell additional features for a price.

## 🎥 Step-by-Step Video Walkthrough 🎬

Follow each step, from server setup, downloading and installing the script, configuring the options, and initiating your own automated claims with the [Video Walkthrough](#videos).

## ☕ If you find this script useful, please consider [buying me a coffee](https://www.buymeacoffee.com/HotWallletBot). Your support is much appreciated and encourages the effort to make everything public.

💡 **HINT:** Some apps allow only one game account per Telegram account. For **HOT**: You can only register **one** blockchain account for **each** Telegram account. However, once the seed phrase has been created and you have made your first claim, you can then log into any game account, using any Telegram account, by using the 12-word seed phrase. This allows you to manage multiple game accounts from a single Telegram or manage each wallet with its own Telegram login if you prefer.

## Install via Docker:
- See the [DOCKER.md](DOCKER.md) file for further instructions. 

## Windows 10 & 11 Users - Utilize WSL2 (tested OK on 20.04 to 24.04 X86/AMD64):
- Download [Ubuntu 24.04](https://www.microsoft.com/store/productId/9NZ3KLHXDJP5) from the Microsoft Store.
- Open PowerShell as an **Administrator** and enable WSL2 with these commands:
   - ```bash
     dism.exe /online /enable-feature /featurename:Microsoft-Windows-Subsystem-Linux /all /norestart
     ```
  - ```bash
    wsl --set-default-version 2
    ```
   - Reboot your computer and open the Ubuntu 24.04 app before following the **Ubuntu** instructions below.
- To make PM2 restart after reboot (optional): Open the Run dialog (```Win + R```), type ```shell:startup```, and copy the ```windows_pm2_restart.bat``` file from the GitHub repository folder into your Windows startup folder. For further details, take a look at the video walkthroughs below.

<a name="quick-start"></a>
## Quick Start Installation (tested on Ubuntu 20.04 to 24.04 X86/AMD64):

Ensure your Operating System is up-to-date by running these commands:

   ```bash
   sudo apt-get update
   sudo apt-get upgrade -y
   sudo reboot
   ```

Execute the QuickStart command block to clone this GitHub, set the Virtual Environment and install all the dependencies: 

   ```bash
   sudo apt install -y git
   git clone https://github.com/thebrumby/HotWalletBot.git
   cd HotWalletBot
   sudo chmod +x install.sh launch.sh
   ./install.sh
   ```
**Ubuntu users only:** Enable PM2 to persist through reboots with the following command (Windows users follow the Windows Guide). 
   ```bash
   pm2 startup systemd
   ```

If you do not have superuser rights, you look at the PM2 output for the prompt to run as a superuser. An example might be:

```sudo env PATH=$PATH:/usr/bin /usr/lib/node_modules/pm2/bin/pm2 startup systemd -u ubuntu --hp /home/ubuntu```

## Games/apps currently working with this script:
**Note: All these scripts assume you have already manually started your selected game, completed any one-time screens that require reading, and made at least 1 claim manually - ensuring you have coins for Gas Fee if necessary**
- ``` ./launch.sh hot``` Launches HOT on Near Protocol: https://t.me/herewalletbot
- ``` ./launch.sh cold``` Launches Cold on BNB Wallet: https://t.me/Newcoldwallet_bot
- ``` ./launch.sh vertus``` Launches Vertus on TON: https://t.me/vertus_app_bot
- ``` ./launch.sh tree``` Launches Tree on BNB Wallet: [https://t.me/treeminebot/app?startapp=6743230454](https://t.me/treeminebot/app?startapp=6783218884)
- ``` ./launch.sh wave``` Launches Wave Wallet on Sui: [https://t.me/waveonsuibot/walletapp?startapp=1809774](https://t.me/waveonsuibot/walletapp?startapp=1809774)

💻 **TIP:** Each session while in wait status uses around 30mb of memory and virtually no CPU load. During the Claim or Login phases, however, each session requires approximately 450 MB of memory and utilizes a larger portion of your CPU resources. The concurrent claims setting (default value 1) limits the number of active claims to prevent hardware overload. Assess your hardware's capacity to determine how many simultaneous sessions it can handle, and adjust the maximum number accordingly by following the [Usage Notes](#usage-notes). Even with a maximum of one allowed claim session, claiming on multiple wallets is easily possible; additional claims just queue until a claim session slot becomes available.
<a name="videos"></a>
| Step-by-Step Video Walkthrough                                                                                                   | YouTube Link                                                                                                                                                                                                                                     | Video Length |
|----------------------------------------------------------------------------------------------------------------------------|---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|--------------|
| **Introduction: Play2Earn - Automating Claims in Telegram Games with Python - Hot, Cold, Vertus, and Tree**  
Dive into the exciting world of Play2Earn games as we explore automation techniques using Python. This video provides a comprehensive walkthrough on how to set up automated claims for games such as Hot, Cold, Vertus, and Tree. Learn how to efficiently manage game rewards and maximize your earnings with our step-by-step guide.       | [![Play2Earn: Automating Claims in Telegram Games with Python - Hot, Cold, Vertus, and Tree](https://img.youtube.com/vi/KzimF-V_mS4/0.jpg)](https://www.youtube.com/watch?v=KzimF-V_mS4)<br>[Watch Video](https://www.youtube.com/watch?KzimF-V_mS4)    | 02:32        |
| **Step 2a: Setting Up an Amazon VPS for Automated Crypto Claiming Scripts**  
Setting up a virtual private server (VPS) on Amazon Web Services is easier than you think! This tutorial covers everything from creating your VPS to configuring it for automated crypto claiming scripts. Whether you're managing Hot, Cold, Vertus, or Tree, these strategies will help streamline your operations and enhance your mining efficiency.      | [![Setting Up an Amazon VPS for Automated Crypto Claiming Scripts](https://img.youtube.com/vi/aXwg8U4Qlvc/0.jpg)](https://www.youtube.com/watch?v=aXwg8U4Qlvc)<br>[Watch Video](https://www.youtube.com/watch?v=aXwg8U4Qlvc)                            | 03:57        |
| **Step 2b: Setting Up Ubuntu on Windows Using WSL for Crypto Automation**  
Learn how to integrate Ubuntu with Windows using the Windows Subsystem for Linux (WSL) for enhanced crypto automation capabilities. This guide will take you through the installation and setup process, showing you how to prepare your system for automating claims in games like Hot, Cold, Vertus, and Tree.       | [![Setting Up Ubuntu on Windows Using WSL for Crypto Automation](https://img.youtube.com/vi/wOajWwO32P4/0.jpg)](https://www.youtube.com/watch?v=wOajWwO32P4)<br>[Watch Video](https://www.youtube.com/watch?v=wOajWwO32P4)                               | 03:47        |
| **Step 3: Installing the Python Script and Configuring Automated Claims**  
Master the setup of automated claiming scripts in this detailed tutorial. We walk you through the installation of necessary Python scripts and show you how to configure them for efficient operation across various games such as Hot, Cold, Vertus, and Tree. This video is perfect for anyone looking to automate their gameplay and claiming process.       | [![Installing the Python Script and Configuring Automated Claims](https://img.youtube.com/vi/Wg2gQBrlCIc/0.jpg)](https://www.youtube.com/watch?v=Wg2gQBrlCIc)<br>[Watch Video](https://www.youtube.com/watch?v=Wg2gQBrlCIc)                             | 06:37        |
| **Step 4: Setting Up Telegram Accounts: QR Codes and One-Time Passwords**  
Setting up Telegram accounts for mining games doesn't have to be complex. This guide demonstrates the use of QR codes and one-time passwords to access games like Hot, Cold, Vertus, and Tree. Follow along to learn how to secure and optimize your game accounts for maximum productivity and ease of use.       | [![Setting Up Telegram Accounts: QR Codes and One-Time Passwords](https://img.youtube.com/vi/gYeiWolV6oY/0.jpg)](https://www.youtube.com/watch?v=gYeiWolV6oY)<br>[Watch Video](https://www.youtube.com/watch?v=gYeiWolV6oY)                          | 03:45        |
| **Mining Hot on Near Protocol - Wallet Setup and Automated Claiming Guide**  
This tutorial focuses on setting up a wallet and automating claims for the Hot game on the Near Protocol blockchain. We'll show you the crucial steps to ensure your wallet is properly configured and automated to claim rewards efficiently. Whether you're a beginner or an experienced miner, these insights will help you make the most of your mining efforts.       | [![Mining Hot on Near Protocol - Wallet Setup and Automated Claiming Guide](https://img.youtube.com/vi/hLBeF4o65KI/0.jpg)](https://www.youtube.com/watch?v=hLBeF4o65KI)<br>[Watch Video](https://www.youtube.com/watch?v=hLBeF4o65KI)                    | 05:42        |
| **Automating Tree Mining with BNB Wallet: Setup and Claims Guide**  
Automate your Tree mining efforts using the BNB Wallet with this straightforward guide. Discover the essential steps for setting up your wallet, initiating claims, and optimizing the process to ensure continuous mining success. This video will equip you with the tools and knowledge needed to effectively manage and automate your mining operations.       | [![Automating Tree Mining with BNB Wallet: Setup and Claims Guide](https://img.youtube.com/vi/YQBemSH3uOA/0.jpg)](https://www.youtube.com/watch?v=YQBemSH3uOA)<br>[Watch Video](https://www.youtube.com/watch?v=YQBemSH3uOA)                            | 03:04        |

<a name="pm2"></a>
### Addional Process Manager 2 ```PM2``` commands you may find useful.  

- View all PM2 managed processes:
    ```bash
    pm2 list
    ```
- View logs for a specific session (Replace `HOT:Wallet1` with the actual name):
    ```bash
    pm2 log HOT:Wallet1
    ```
- To remove a managed wallet:
    ```bash
    pm2 delete HOT:Wallet1
    ```
- Save configuration if you add or delete processes:
    ```bash
    pm2 save
    ```

<a name="usage-notes"></a>
## V3.0.0 Release Notes. 

## Usage Instructions
After executing the script with ```./launch.sh```, you will be prompted to update settings and configure the session:

### Update Settings
   - If you choose "yes" to update settings when prompted, you can review and possibly update the following settings:
      - `forceClaim`: Choose to force a claim the first time the script runs, regardless of whether the wallet is full.
      - `debugIsOn`: Activate debugging to save screenshots locally; default is off.
      - `hideSensitiveInput`: Ensures sensitive information like phone numbers and seed phrases remain hidden; default is ON.
      - `screenshotQRCode`: Prefer to log in via QR code; the alternative is manual login via phone number and OTP.
      - `maxSessions`: Set the maximum number of concurrent claim sessions; additional wallets will wait for an available slot.
      - `verboseLevel`: Adjust the verbosity of console messages; options range from 1 (minimal) to 3 (all messages).
      - `forceNewSession`: Forces a new login, useful if the existing session encounters errors.
      - `lowestClaimOffset` and `highestClaimOffset`: Define the range for randomized claim timing relative to when the pot is filled.
         - **Examples of Random Claim Timing based on Claim Offset:**
            - `-30, -15`: Early claims randomly between 30 and 15 minutes before the pot is full.
            - `30, 60`: Late claims randomly 30 minutes to 1 hour after the pot is full.
            - `-15, 15`: Random claims within a 15-minute window either side of the pot being filled.

### Session Name Configuration
   - Sessions are auto-named numerically in the format "Wallet1", or can be customized to your own choice. Reusing a name attempts to resume that session.

### Telegram Login: Saved Account Options
   - If the script detects you have a saved Telegram session, you can choose it from a numbered list. 
   - If you prefer to log into a new account, selecting 'n' proceeds to a new Telegram login. The default method is to log in by scanning a QR Code screenshot.
   - Should the QR Code method be unsuccessful, or if you disable it in settings, follow the OTP login procedure outlined below.

### Telegram OTP login: Country Name and Phone Number for Telegram
   - Enter your Country Name as displayed on Telegram's login page or accept the default, which is auto-detected based on your IP.

### Telegram OTO login: One-Time Password (OTP)
   - Enter the OTP sent to your registered Telegram account.

### Telegram login: Two-factor authentication (2FA)
   - If 2FA is enabled on your Telegram account, enter your 2FA password following the QR code scan or OTP entry.

### Game login: Seed Phrase Input for HereWalletBot Login
   - If your selected game requires a seed phrase to log in, carefully input your 12-word seed phrase, ensuring correct spacing without any punctuation or numbers.
   - Alternatively, if the game's login is based on the Telegram account, ensure you are logging into the correct account.

### Final options once the PM2 session is configured.
   - Select "a" or press <enter> to automatically add the session to PM2.
   - Select "e" to exit to the Command Line Interface without adding to PM2
   - Select "y" to continue and attempt to make a claim. 

Remember to check and adjust your settings upon startup to optimize the script's performance to your server's capabilities.

After following these steps, if all inputs are correctly entered, and assuming no flooding block is in place, you'll be successfully logged into Telegram and your chosen game.

# Security Considerations for HotWalletClaimer Usage

💡 Communication: The only external communication is with the Telegram Web App, which occurs over HTTPS, providing a secure channel.

⚠️ Your seed phrase and Telegram login details are not stored or transmitted by this script, except during the unavoidable one-time login process. As of version v1.3.4, the Google Chrome session is now saved into the ```selenium``` folder, as of v.1.3.6 there is also a duplicate of the session in ```./HotWalletBot/backups``` - if this information were to become compromised, it would allow a suitably experienced individual to access your account.  

💡 Debugging: Enabling debug mode captures the whole process as screenshots, excluding the seed phrase entry step. These images are stored locally to assist you in the event of errors and are not otherwise transmitted or uploaded in any way.

## Security Best Practice:

💡 Private Devices: Only use this script on private, secure machines or Virtual Private Servers that only you can access.

⚠️ Caution with Seed Phrases: Be very cautious with accounts of significant value. Consider the effect of any unintended loss should your seed phrase become compromised.

💡 Awareness and Discretion: Understand the security trade-offs of using this automation tool or any other third-party tools. Your vigilance is crucial in safeguarding your information.

## Disclaimer:
Use of HotWalletClaimer is at your own risk. While we are confident that the script neither transmits nor stores your sensitive data, it is essential to acknowledge that devices can become compromised through viruses or other malicious software. The developers of HotWalletClaimer exclude any liability for potential security breaches or financial losses. It is your responsibility to safeguard your digital security. Always prioritize protecting your accounts and sensitive information.

