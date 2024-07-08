#!/bin/bash

# Update package list
sudo apt update

# Install basic dependencies
sudo apt install -y snapd curl wget python3 python3-pip libzbar0 unzip python3-venv gdebi-core || true
sudo systemctl daemon-reload

# Create a virtual environment and install dependencies
python3 -m venv venv
source venv/bin/activate
pip install wheel selenium Pillow pyzbar qrcode-terminal python-telegram-bot requests mitmproxy
deactivate

# Installing Node.js and npm
curl -fsSL https://deb.nodesource.com/setup_current.x | sudo -E bash -
sudo apt-get install -y nodejs || true

# Install pm2 globally
sudo npm install pm2@latest -g

install_chromium_arm64() {
    sudo apt-get clean
    sudo apt-get autoclean
    sudo rm -rf /var/lib/apt/lists/
    sudo apt update
    sudo apt-get install xdg-utils libasound2-dev -y
    # Fetch and install chromium-codecs-ffmpeg-extra
    wget http://launchpadlibrarian.net/660838579/chromium-codecs-ffmpeg-extra_112.0.5615.49-0ubuntu0.18.04.1_arm64.deb
    sudo gdebi -n chromium-codecs-ffmpeg-extra_112.0.5615.49-0ubuntu0.18.04.1_arm64.deb

    # Fetch and install chromium-browser
    wget http://launchpadlibrarian.net/660838574/chromium-browser_112.0.5615.49-0ubuntu0.18.04.1_arm64.deb
    sudo gdebi -n chromium-browser_112.0.5615.49-0ubuntu0.18.04.1_arm64.deb

    # Fetch and install chromium-chromedriver
    wget http://launchpadlibrarian.net/660838578/chromium-chromedriver_112.0.5615.49-0ubuntu0.18.04.1_arm64.deb
    sudo gdebi -n chromium-chromedriver_112.0.5615.49-0ubuntu0.18.04.1_arm64.deb
}

install_chromium_x86_64() {
    sudo apt install -y chromium-browser chromium-chromedriver
}

install_google_chrome() {
    wget -O /tmp/chrome.deb https://mirror.cs.uchicago.edu/google-chrome/pool/main/g/google-chrome-stable/google-chrome-stable_126.0.6478.114-1_amd64.deb
    sudo dpkg -i /tmp/chrome.deb
    sudo apt-get install -f -y  # Fix any dependency issues
    rm /tmp/chrome.deb
}

install_chromedriver() {
    sudo apt install -y unzip || true  # Ensure unzip is installed
    wget https://storage.googleapis.com/chrome-for-testing-public/126.0.6478.63/linux64/chromedriver-linux64.zip
    unzip chromedriver-linux64.zip
    rm chromedriver-linux64.zip
    sudo mv chromedriver-linux64/chromedriver /usr/local/bin/
    sudo chmod +x /usr/local/bin/chromedriver
}

prompt_swap_browser() {
    local current_browser=$1
    local new_browser=$2
    local install_function=$3

    read -p "Would you like to swap from $current_browser to $new_browser? (y/N): " response
    if [[ "$response" =~ ^([yY][eE][sS]|[yY])$ ]]; then
        echo "Switching from $current_browser to $new_browser..."
        sudo apt-get remove -y chromium-browser google-chrome-stable
        $install_function
    else
        echo "Keeping $current_browser..."
    fi
}

ARCH=$(uname -m)

if [[ "$ARCH" == "x86_64" ]]; then
    # Variables to check installation status
    GOOGLE_CHROME_INSTALLED=false
    CHROMIUM_INSTALLED=false

    # Check if Google Chrome is installed
    if google-chrome --version &>/dev/null; then
        GOOGLE_CHROME_INSTALLED=true
        CHROME_VERSION=$(google-chrome --version | grep -oP '(?<=Google Chrome\s)[\d.]+')
        echo "Google Chrome is already installed. Version: $CHROME_VERSION"
    fi

    # Check if Chromium is installed
    if chromium-browser --version &>/dev/null; then
        CHROMIUM_INSTALLED=true
        CHROME_VERSION=$(chromium-browser --version | grep -oP '(?<=Chromium\s)[\d.]+')
        echo "Chromium is already installed. Version: $CHROME_VERSION"
    fi

    # Prompt to swap browsers if both are installed
    if $GOOGLE_CHROME_INSTALLED && $CHROMIUM_INSTALLED; then
        prompt_swap_browser "Google Chrome" "Chromium" install_chromium_x86_64
    elif $GOOGLE_CHROME_INSTALLED; then
        prompt_swap_browser "Google Chrome" "Chromium" install_chromium_x86_64
    elif $CHROMIUM_INSTALLED; then
        prompt_swap_browser "Chromium" "Google Chrome" install_google_chrome
    else
        echo "Neither Google Chrome nor Chromium is installed. Installing Chromium..."
        install_chromium_x86_64
    fi

    # Check if Chromedriver is installed
    if chromedriver --version &>/dev/null; then
        CHROMEDRIVER_VERSION=$(chromedriver --version | grep -oP '(?<=ChromeDriver\s)[\d.]+')
        echo "Chromedriver is already installed. Version: $CHROMEDRIVER_VERSION"
    else
        echo "Chromedriver is not installed. Installing now..."
        install_chromedriver
    fi
elif [[ "$ARCH" == "aarch64" ]]; then
    # Check if Chromium is installed
    if chromium-browser --version &>/dev/null; then
        CHROME_VERSION=$(chromium-browser --version | grep -oP '(?<=Chromium\s)[\d.]+')
        echo "Chromium is already installed. Version: $CHROME_VERSION"
    else
        echo "Chromium is not installed. Installing now..."
        install_chromium_arm64
    fi

    # Check if Chromedriver is installed
    if chromedriver --version &>/dev/null; then
        CHROMEDRIVER_VERSION=$(chromedriver --version | grep -oP '(?<=ChromeDriver\s)[\d.]+')
        echo "Chromedriver is already installed. Version: $CHROMEDRIVER_VERSION"
    else
        echo "Chromedriver is not installed. Installing now..."
        install_chromium_arm64
    fi
else
    echo "Unsupported architecture: $ARCH"
    exit 1
fi

# Fetch and show the installed versions
if google-chrome --version &>/dev/null; then
    CHROME_VERSION=$(google-chrome --version | grep -oP '(?<=Google Chrome\s)[\d.]+')
elif chromium-browser --version &>/dev/null; then
    CHROME_VERSION=$(chromium-browser --version | grep -oP '(?<=Chromium\s)[\d.]+')
fi

CHROMEDRIVER_VERSION=$(chromedriver --version | grep -oP '(?<=ChromeDriver\s)[\d.]+')

echo ""
echo "Installed Versions:"
echo "PM2 version: $(pm2 --version)"
echo "Python version: $(python3 --version 2>/dev/null || echo 'Python 3 not found')"
echo "Node.js version: $(node --version 2>/dev/null || echo 'Node.js not found')"
echo "npm version: $(npm --version 2>/dev/null || echo 'npm not found')"
echo "Chromium/Chrome version: $CHROME_VERSION"
echo "Chromedriver version: $CHROMEDRIVER_VERSION"
echo "Architecture: $ARCH"
echo "Note: x86_64 users can run this script again to switch between Google Chrome/Chromium browsers."
