# Docker Setup for Telegram Claim Bot

Using Docker simplifies the setup of the Telegram Claim Bot by containerizing the application and its dependencies. This ensures a consistent environment across different architectures (X86/ARM64) and operating systems (Linux-based/Windows), and eliminates issues related to dependency management and version conflicts. Docker also provides an easy way to deploy, scale, and manage the application, making it an ideal choice for running the Telegram Claim Bot efficiently.

To get started with Docker, you need to have Docker installed on your device. See the Linux Installation examples for Amazon Linux and Ubuntu below. For Windows machines, you can download and install Docker Desktop from [Docker's official website](https://www.docker.com/products/docker-desktop/).

## To Install:
```sh
docker run -d --ulimit nofile=32768 --name telegram-claim-bot thebrumby/telegram-claim-bot:1:0
```
## To Interact with the Script, Including Adding Accounts or Monitoring:
```sh
docker exec -it telegram-claim-bot /bin/bash
```
## To Add a Game:
```sh
# To pick from a list of available scripts:
./launch.sh
# or to specify the script by name:
./launch.sh hot
```
## To Update for the Latest Code or New Games:
```sh
./pull-games.sh
```
## To See the Currently Running Games (if any):
```sh
pm2 list
```
## To See the Output from the Games (to Monitor):
```sh
pm2 logs 
# or for specific logs
pm2 logs 1
# or by name
pm2 logs HOT:Wallet1
```
## To Start the Session After a Reboot or Stopping:
```sh
docker start telegram-claim-bot
docker exec -it telegram-claim-bot /bin/bash
```
## To Remove the Container:
```sh
docker stop telegram-claim-bot
docker rm telegram-claim-bot
```
All other instructions are in line with the main [README.md](https://github.com/thebrumby/HotWalletClaimer).

# Linux Setup Examples:

## First run only: Open the Terminal via SSH and run these commands.

### Step 1 (Amazon Linux) - Install Docker and Add the current user to the Docker group:
```sh
sudo yum update -y
sudo yum install docker -y
sudo service docker start
sudo usermod -aG docker $USER
exit
```
### Step 1 (Ubuntu) - Install Docker and Add the current user to the Docker group:
```sh
sudo apt-get update -y
sudo apt-get install docker.io -y
sudo systemctl start docker
sudo systemctl enable docker
sudo usermod -aG docker $USER
exit
```
### Step 2 - Open the Terminal again and start the Claim Bot
#### Note: `--restart unless-stopped` is set in this example, to restart the container on reboot etc
```sh
docker run -d --ulimit nofile=32768 --name telegram-claim-bot --restart unless-stopped thebrumby/telegram-claim-bot:1.0
```
### Step 3 - Interact with the Docker Container
To interact with the script, including adding accounts or monitoring, use:
```sh
docker exec -it telegram-claim-bot /bin/bash
```
### To Exit the Docker and Return to the Amazon Linux CLI:
Press `Ctrl + D` or type:
`exit`

### Follow the instructions at the top of the page for details on how to interact with the script.
