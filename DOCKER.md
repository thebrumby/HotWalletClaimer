# Docker Setup for Telegram Claim Bot

Prerequisite: You must have Docker installed on your intended device.

## To Install:
```sh
docker run -d --ulimit nofile=32768 --name telegram-claim-bot thebrumby/telegram-claim-bot:1.0
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


