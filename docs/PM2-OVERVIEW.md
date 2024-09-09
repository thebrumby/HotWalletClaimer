# PM2 Overview

## Introduction to PM2
PM2 (Process Manager 2) is a production-grade process manager for Node.js applications. It helps you manage and monitor your applications to keep them online indefinitely, offering features like automatic restarts, log management, and clustering.

This guide will walk you through the basics of PM2, more advanced uses like pattern matching, configuring log rotation, and OS-specific tips for both Ubuntu and Windows users.

## 1. Basic PM2 Commands

Here are some essential commands to get started with PM2:

- **List all processes managed by PM2**:  
  ```
  pm2 list
  ```
  <img width="554" alt="image" src="https://github.com/user-attachments/assets/b2765895-208d-47b9-a39c-f5a03554a914">

- **Start an existing stopped process**: `pm2 start <game_session>` or `pm2 start <ID>` or `pm2 start all`. Example:
  ```
  pm2 start Blum:Phil
  ```
  ```
  pm2 start 46
  ```
  ```
  pm2 start all
  ```

- **View logs for a specific process**: `pm2 log <game_session>` or `pm2 log <ID>` or `pm2 log` for all processes
  ```
  pm2 log 
  ```

- **Restart a process**: `pm2 restart <game_session>` or `pm2 restart <ID>` or `pm2 restart all`
  ```
  pm2 restart Vertus:Wallet2
  ```

- **Delete a process from PM2**: `pm2 delete <game_session>` or `pm2 delete <ID>` or `pm2 delete all`
  ```
  pm2 delete Cryptorank:Wallet1
  ```

- **Save the current process list** (after adding or removing processes):  
  ```
  pm2 save
  ```

## 2. Advanced PM2 Commands (Pattern Matching)

PM2 supports pattern matching, which is useful when managing multiple similar processes. This only works with the **stop** and **restart** commands:

- **Restart processes using pattern matching**:  
  ```
  pm2 restart /pattern/
  ```

  Example to start all HOT games regardless of the account/session name:
  ```
  pm2 restart /HOT:/
  ```
  This would restart: HOT:Wallet1 HOT:Wallet2 HOT:Wallet3 etc.

  Example to stop all account sessions of a certain name regardless of the game:
  ```
  pm2 stop /:Wallet1/
  ```
  This would stop: HOT:Wallet1, Vertus:Wallet1, HammyKombat:Wallet1, etc.

## 3. Configuring PM2 Log Rotation

PM2 can manage log files to prevent them from consuming too much disk space.

To configure PM2 log rotation, follow the detailed guide in the separate [PM2-LOGS.md](https://github.com/thebrumby/HotWalletClaimer/blob/main/docs/PM2-LOGS.md).

## 4. Ensuring PM2 Persistence Through Reboots

### For Ubuntu Users (excluding Docker which is pre-configured):

To ensure PM2 persists through reboots, run the following command:
```
pm2 startup systemd
```

If you don't have superuser rights, PM2 will prompt you to run a command with `sudo`. Here’s an example of what that might look like:
```
sudo env PATH=$PATH:/usr/bin /usr/lib/node_modules/pm2/bin/pm2 startup systemd -u ubuntu --hp /home/ubuntu
```

### For Windows Users:

To make PM2 restart automatically after a system reboot:

1. Open the Run dialog by pressing `Win + R`.
2. Type `shell:startup` and press Enter.
3. Copy the `windows_pm2_restart.bat` file from your GitHub repository into your Windows startup folder.

This will ensure PM2 is automatically restarted on reboot.

### For more detailed information about each OS, follow the dedicated guide in the docs folder of this repository or watch the instructional videos.

## 5. Setting Limits on Disk Usage with Log Rotation

To manage the size of logs and prevent them from filling up your disk, you can configure PM2's log rotation feature. Refer to the [PM2-LOGS.md](https://github.com/thebrumby/HotWalletClaimer/blob/main/docs/PM2-LOGS.md) document for in-depth configuration details.

```
pm2 install pm2-logrotate
pm2 set pm2-logrotate:max_size 100M
pm2 set pm2-logrotate:retain 30
```

This will ensure that logs are rotated when they reach 100MB, and PM2 will retain the last 30 rotated logs.

For further details, you can explore the PM2 documentation or check the example scripts in this repository.
