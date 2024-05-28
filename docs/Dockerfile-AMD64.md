# Dockerfile 1.1
## Based on AMD 64 build
### Next step: remove games update from the build



##### Use Ubuntu as the base image
```
FROM ubuntu:24.04
```

##### Set environment variables to avoid interactive prompts
```
ENV DEBIAN_FRONTEND=noninteractive
```

##### Install basic dependencies including unzip and required libraries for ChromeDriver
```
RUN apt-get update && \
    apt-get install -y wget curl gnupg2 ca-certificates xdg-utils libasound2-dev git unzip \
    libglib2.0-0 libnss3 libfontconfig1 libx11-xcb1 libxcomposite1 libxcursor1 libxdamage1 \
    libxi6 libxtst6 libappindicator3-1 libxrandr2 libatk1.0-0 libcups2 libpangocairo-1.0-0 \
    libpango-1.0-0 libgtk-3-0 libdrm2 libgbm1 libxshmfence1 fonts-liberation libatk-bridge2.0-0 \
    libatspi2.0-0 libu2f-udev libvulkan1 libxfixes3 libxkbcommon0 --no-install-recommends && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*
```

##### Install Node.js (latest) and PM2
```
RUN curl -fsSL https://deb.nodesource.com/setup_current.x -o nodesource_setup.sh && \
    bash nodesource_setup.sh && \
    apt-get install -y nodejs && \
    npm install -g pm2 && \
    rm nodesource_setup.sh
```

##### Install Google Chrome
```
RUN wget -O /tmp/chrome.deb https://mirror.cs.uchicago.edu/google-chrome/pool/main/g/google-chrome-stable/google-chrome-stable_125.0.6422.76-1_amd64.deb && \
    dpkg -i /tmp/chrome.deb && \
    apt-get install -f -y  # Fix any dependency issues && \
    rm /tmp/chrome.deb
```

##### Verify Chrome installation
```
RUN google-chrome --version
```

##### Install Chromedriver
```
RUN wget -O /tmp/chromedriver.zip https://storage.googleapis.com/chrome-for-testing-public/125.0.6422.76/linux64/chromedriver-linux64.zip && \
    unzip /tmp/chromedriver.zip -d /tmp/ && \
    mv /tmp/chromedriver-linux64/chromedriver /usr/local/bin/chromedriver && \
    chmod +x /usr/local/bin/chromedriver && \
    rm -rf /tmp/chromedriver.zip /tmp/chromedriver-linux64
```

##### Verify Chromedriver installation
```
RUN chromedriver --version
```

##### Copy the shell script to update /games from the GitHub if it contains updates
```
COPY pull-games.sh /usr/src/app/pull-games.sh
RUN chmod +x /usr/src/app/pull-games.sh
RUN /usr/src/app/pull-games.sh
```

##### Copy the shell script to run a daily update
```
COPY update.sh /usr/src/app/
RUN chmod +x /usr/src/app/update.sh
```

##### Copy the shell script to tidy up directories
```
COPY remove-process.sh /usr/src/app/
RUN chmod +x /usr/src/app/update.sh
```

##### Get general dependencies 
```
RUN apt install -y snapd curl wget python3 python3-pip libzbar0 unzip python3-venv gdebi-core
```

##### Create and activate a virtual environment within the app directory, then install Python packages
```
WORKDIR /usr/src/app
RUN python3 -m venv venv && \
    venv/bin/pip install wheel selenium Pillow pyzbar qrcode-terminal
```

##### Copy the launch script and make it executable
```
COPY launch.sh /usr/src/app/
RUN chmod +x /usr/src/app/launch.sh
```

##### Ensure the virtual environment's Python interpreter is in the PATH
```
ENV PATH="/usr/src/app/venv/bin:$PATH"
```

##### Copy the PM2 ecosystem configuration file
```
COPY ecosystem.config.js /usr/src/app/
```

##### Ensure PM2 resurrects saved process list on startup
```
CMD ["sh", "-c", "pm2 resurrect && pm2-runtime start ecosystem.config.js"]
```
