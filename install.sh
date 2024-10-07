#!/bin/bash

# Update package list
sudo apt update

# Upgrade Python to the latest version
sudo apt install -y python3 python3-pip python3-venv

# Install or upgrade basic dependencies
sudo apt install -y snapd curl wget libzbar0 unzip gdebi-core || true
sudo systemctl daemon-reload

# Remove existing virtual environment if it exists
rm -rf venv

# Create a new virtual environment and install/upgrade Python packages
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip wheel
pip install --upgrade selenium Pillow pyzbar qrcode-terminal python-telegram-bot requests mitmproxy
deactivate

# Installing Node.js and npm
curl -fsSL https://deb.nodesource.com/setup_current.x | sudo -E bash -
sudo apt-get install -y nodejs || true

# Install pm2 globally
sudo npm install pm2@latest -g

# Install or upgrade Chromium/Google Chrome and Chromedriver depending on architecture
install_chromium_arm64() {
    sudo apt-get clean
    sudo apt-get autoclean
    sudo rm -rf /var/lib/apt/lists/
    sudo apt update
    sudo apt-get install xdg-utils libasound2-dev -y
    wget http://launchpadlibrarian.net/660838579/chromium-codecs-ffmpeg-extra_112.0.5615.49-0ubuntu0.18.04.1_arm64.deb
    sudo gdebi -n chromium-codecs-ffmpeg-extra_112.0.5615.49-0ubuntu0.18.04.1_arm64.deb

    wget http://launchpadlibrarian.net/660838574/chromium-browser_112.0.5615.49-0ubuntu0.18.04.1_arm64.deb
    sudo gdebi -n chromium-browser_112.0.5615.49-0ubuntu0.18.04.1_arm64.deb

    wget http://launchpadlibrarian.net/660838578/chromium-chromedriver_112.0.5615.49-0ubuntu0.18.04.1_arm64.deb
    sudo gdebi -n chromium-chromedriver_112.0.5615.49-0ubuntu0.18.04.1_arm64.deb
}

install_chromium_x86_64() {
    sudo apt install -y chromium-browser chromium-chromedriver
}

install_google_chrome() {
    wget -O /tmp/chrome.deb https://mirror.cs.uchicago.edu/google-chrome/pool/main/g/google-chrome-stable/google-chrome-stable_129.0.6668.89-1_amd64.deb
    sudo dpkg -i /tmp/chrome.deb
    sudo apt-get install -f -y
    rm /tmp/chrome.deb
}

install_chromedriver() {
    sudo apt install -y unzip || true
    wget https://storage.googleapis.com/chrome-for-testing-public/129.0.6668.89/linux64/chromedriver-linux64.zip
    unzip chromedriver-linux64.zip
    rm chromedriver-linux64.zip
    sudo mv chromedriver-linux64/chromedriver /usr/local/bin/
    sudo chmod +x /usr/local/bin/chromedriver
}

ARCH=$(uname -m)

if [[ "$ARCH" == "x86_64" ]]; then
    if ! google-chrome --version &>/dev/null; then
        install_google_chrome
    else
        echo "Google Chrome is already installed."
    fi
    install_chromedriver
elif [[ "$ARCH" == "aarch64" ]]; then
    install_chromium_arm64
else
    echo "Unsupported architecture: $ARCH"
    exit 1
fi

# Fetch and display installed versions
echo ""
echo "Installed Versions:"
echo "PM2 version: $(pm2 --version)"
echo "Python version: $(python3 --version)"
echo "Node.js version: $(node --version)"
echo "npm version: $(npm --version)"
echo "Chromium/Chrome version: $(chromium-browser --version || google-chrome --version)"
echo "Chromedriver version: $(chromedriver --version)"
echo "Architecture: $ARCH"
