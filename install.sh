#!/bin/bash

# Update package list
sudo apt update

# Install basic dependencies
sudo apt install -y snapd curl wget python3 python3-pip libzbar0 unzip python3-venv || true
sudo systemctl daemon-reload

# Create a virtual environment and install dependencies
python3 -m venv venv
source venv/bin/activate
pip install wheel selenium Pillow pyzbar qrcode-terminal
deactivate

# Installing Node.js and npm
curl -fsSL https://deb.nodesource.com/setup_current.x | sudo -E bash -
sudo apt-get install -y nodejs || true

# Install pm2 globally
sudo npm install pm2@latest -g

install_chrome() {
    wget -O /tmp/chrome.deb https://mirror.cs.uchicago.edu/google-chrome/pool/main/g/google-chrome-stable/google-chrome-stable_124.0.6367.91-1_amd64.deb
    sudo dpkg -i /tmp/chrome.deb
    sudo apt-get install -f -y  # Fix any dependency issues
    rm /tmp/chrome.deb
}

install_chromedriver() {
    sudo apt install -y unzip || true  # Ensure unzip is installed
    wget https://storage.googleapis.com/chrome-for-testing-public/124.0.6367.91/linux64/chromedriver-linux64.zip
    unzip chromedriver-linux64.zip
    rm chromedriver-linux64.zip
    sudo mv chromedriver /usr/local/bin/
    sudo chmod +x /usr/local/bin/chromedriver
}

# Check if Google Chrome is installed (any version)
if google-chrome --version &>/dev/null; then
    CHROME_VERSION=$(google-chrome --version | grep -oP '(?<=Google Chrome\s)[\d.]+')
    echo "Google Chrome is already installed. Version: $CHROME_VERSION"
else
    echo "Google Chrome is not installed. Installing now..."
    install_chrome
fi

# Check if ChromeDriver is installed (any version)
if chromedriver --version &>/dev/null; then
    CHROMEDRIVER_VERSION=$(chromedriver --version | grep -oP '(?<=ChromeDriver\s)[\d.]+')
    echo "ChromeDriver is already installed. Version: $CHROMEDRIVER_VERSION"
else
    echo "ChromeDriver is not installed. Installing now..."
    install_chromedriver
fi

# Fetch and show the installed versions
CHROME_VERSION=$(google-chrome --version | grep -oP '(?<=Google Chrome\s)[\d.]+')
CHROMEDRIVER_VERSION=$(chromedriver --version | grep -oP '(?<=ChromeDriver\s)[\d.]+')

echo ""
echo "Installed Versions:"
echo "PM2 version: $(pm2 --version)"
echo "Python version: $(python3 --version 2>/dev/null || echo 'Python 3 not found')"
echo "Node.js version: $(node --version 2>/dev/null || echo 'Node.js not found')"
echo "npm version: $(npm --version 2>/dev/null || echo 'npm not found')"
echo "Google Chrome version: $CHROME_VERSION"
echo "ChromeDriver version: $CHROMEDRIVER_VERSION"