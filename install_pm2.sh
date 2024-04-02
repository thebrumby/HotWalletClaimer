#!/bin/bash

# Update package lists
sudo apt update

# Install prerequisites (curl, software-properties-common) for Node.js setup
sudo apt install -y curl software-properties-common

# Add NodeSource repository for recent Node.js versions 
curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -

# Install Node.js and npm
sudo apt install -y nodejs

# Verify Node.js and npm installation
echo "Node.js version:"
node -v
echo "npm version:"
npm -v

# Install PM2 globally
sudo npm install pm2 -g

# Provide a usage example 
echo "----------------------"
echo "PM2 Installed Successfully!"
echo "To start your script with an argument: pm2 start claim.py yourSessionID1 --name 'my-instance1'"
echo "(Replace 'yourSessionID1' with the actual session ID and repeat as necessry)"
echo "For further PM2 usage: pm2 --help"
