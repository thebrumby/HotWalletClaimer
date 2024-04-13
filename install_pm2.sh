#!/bin/bash

# Update and install prerequisites
echo "Updating package index..."
sudo apt update

echo "Installing prerequisites..."
sudo apt install -y curl

# Adding NodeSource repository
echo "Adding NodeSource repository for Node.js..."
curl -fsSL https://deb.nodesource.com/setup_current.x | sudo -E bash -

# Installing Node.js and npm
echo "Installing Node.js and npm..."
sudo apt-get install -y nodejs

# Verifying Node.js installation
echo "Node.js version:"
node --version

# Verifying npm installation
echo "npm version:"
npm --version

# Installing PM2
echo "Installing PM2 with npm..."
sudo npm install pm2@latest -g

# Verifying PM2 installation
echo "PM2 version:"
pm2 --version

echo "Start PM2 as a service: pm2 startup systemd"
echo "Add a first session: pm2 start claim.py --name firstWallet -- 1"
echo "Add a second session: pm2 start claim.py --name secondWallet -- 2"
echo "Save the PM2 list, it will persist through reboots: pm2 save"
echo "See the current list of processes managed by PM2: pm2 list"
echo "Remove a wallet from PM2: pm2 delete firstWallet"
echo "Remove PM2 as a service: pm2 unstartup systemd"
