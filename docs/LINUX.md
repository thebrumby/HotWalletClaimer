## Stand-alone Linux Installation (Ubuntu 20.04 to 24.04):

Ensure your Operating System is up-to-date by running these commands:
```bash
   sudo apt-get update
   sudo apt-get upgrade -y
   sudo reboot
```

Execute the QuickStart command block to clone this GitHub repository, set up the Virtual Environment, and install all the dependencies:
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

By following these steps, you will have a fully functional environment to run the Telegram Claim Bot on your Ubuntu system. Make sure to check the [DOCKER.md](docs/DOCKER.md) file for detailed instructions on using Docker if preferred.
