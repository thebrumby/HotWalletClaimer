FROM ubuntu:24.04

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && \
    apt-get install -y wget curl gnupg2 ca-certificates xdg-utils libasound2-dev git unzip \
    libglib2.0-0 libnss3 libfontconfig1 libx11-xcb1 libxcomposite1 libxcursor1 libxdamage1 \
    libxi6 libxtst6 libappindicator3-1 libxrandr2 libatk1.0-0 libcups2 libpangocairo-1.0-0 \
    libpango-1.0-0 libgtk-3-0 libdrm2 libgbm1 libxshmfence1 fonts-liberation libatk-bridge2.0-0 \
    libatspi2.0-0 libu2f-udev libvulkan1 libxfixes3 libxkbcommon0 --no-install-recommends && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

RUN curl -fsSL https://deb.nodesource.com/setup_current.x -o nodesource_setup.sh && \
    bash nodesource_setup.sh && \
    apt-get update && apt-get install -y nodejs && \
    npm install -g pm2 && \
    rm nodesource_setup.sh && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

RUN wget -O /tmp/chrome.deb https://mirror.cs.uchicago.edu/google-chrome/pool/main/g/google-chrome-stable/google-chrome-stable_125.0.6422.76-1_amd64.deb && \
    dpkg -i /tmp/chrome.deb && \
    apt-get update && apt-get install -f -y  # Fix any dependency issues && \
    rm /tmp/chrome.deb  && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

RUN google-chrome --version

RUN wget -O /tmp/chromedriver.zip https://storage.googleapis.com/chrome-for-testing-public/125.0.6422.76/linux64/chromedriver-linux64.zip && \
    unzip /tmp/chromedriver.zip -d /tmp/ && \
    mv /tmp/chromedriver-linux64/chromedriver /usr/local/bin/chromedriver && \
    chmod +x /usr/local/bin/chromedriver && \
    rm -rf /tmp/chromedriver.zip /tmp/chromedriver-linux64

RUN chromedriver --version

COPY docker/* /usr/src/app/
COPY launch.sh /usr/src/app/

RUN apt-get update && apt-get install -y 
    snapd curl wget python3 python3-pip libzbar0 unzip python3-venv gdebi-core  && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /usr/src/app
RUN python3 -m venv venv && \
    venv/bin/pip install wheel selenium Pillow pyzbar qrcode-terminal flask

ENV PATH="/usr/src/app/venv/bin:$PATH"

CMD ["/bin/bashbash", "-c", "pm2 resurrect && pm2-runtime start ecosystem.config.js"]
