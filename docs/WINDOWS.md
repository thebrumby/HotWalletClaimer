## Windows Guide for Setting Up Ubuntu 24.04 with WSL2

This guide will help you set up Ubuntu 24.04 on your Windows PC using Windows Subsystem for Linux 2 (WSL2). This setup allows you to run a Linux distribution natively on your Windows machine.

### Prerequisites

Before starting, ensure that your Windows version supports WSL2. You need Windows 10, version 2004, Build 19041 or higher, or Windows 11.

### Step-by-Step Instructions

1. **Download Ubuntu 24.04**

   Download [Ubuntu 24.04](https://www.microsoft.com/store/productId/9NZ3KLHXDJP5) from the Microsoft Store.

2. **Enable WSL2**

   Open PowerShell as an **Administrator** and enable WSL2 with the following commands:

   ```powershell
   dism.exe /online /enable-feature /featurename:Microsoft-Windows-Subsystem-Linux /all /norestart
   ```
### Set WSL2 as the default version:

   ```powershell
   wsl --set-default-version 2
   ```

Reboot your computer and open the Ubuntu 24.04 app before following the Ubuntu instructions below.

### Optional: Configure PM2 to Restart After Reboot

To make PM2 restart after a reboot, you can set up a startup script:

1. Open the Run dialog by pressing `Win + R`, type `shell:startup`, and press Enter.
2. Copy the `windows_pm2_restart.bat` file from your GitHub repository folder into your Windows startup folder.

This script ensures that PM2 restarts automatically after a system reboot. For further details, refer to the video walkthroughs linked below.

### Additional Resources

For a more detailed walkthrough, consider watching the following video tutorials:

- [WSL2 Setup and Configuration](#)
- [Using PM2 with WSL2](#)

By following these steps, you should have a fully functional Ubuntu 24.04 environment running on WSL2, allowing you to take advantage of Linux tools and workflows directly from your Windows PC.
