# Telegram Claim Bot - Proxy Support Instructions

## Introduction

The Telegram Claim Bot now supports a **third-party proxy tunnel**. This optional feature allows you to:

- **Bypass geo-location restrictions** that may prevent access to social media like Telegram Web.
- **Enhance privacy** by routing your bot's activities through various locations.

Follow the steps below to enable and configure proxy support for your bot.

---

## 1. Enabling Proxy Support

Ensure you are in the main directory where you launch your scripts. Execute the following commands to enable proxy support:

```
./launch.sh enable-proxy
```

Then, set up your proxy configuration with:

```
./launch.sh setup-proxy
```

---

## 2. Configuring Your Proxy

During the setup process, you will be prompted to provide your proxy details. If an existing proxy configuration is detected, it will be displayed, and you can choose to **retain or remove** it.

**Provide the following information when prompted:**

- **Upstream proxy host (IP or URL):**
- **Upstream proxy port:**
- **Upstream proxy username:**
- **Upstream proxy password:**

**Process:**

1. **Enter Proxy Details:** Input your proxy credentials as prompted.
2. **Connection Test:** The script will attempt to establish a connection using the provided details.
   - **Success:** The built-in proxy will restart and authenticate with your proxy server.
   - **Failure:** An error message will appear, pompting you to re-enter the correct information.

**Example:**

- Enter upstream proxy host (IP or URL): proxy.example.com
- Enter upstream proxy port: 8080
- Enter upstream proxy username: yourUsername
- Enter upstream proxy password: yourPassword

---

## 3. Updating In-Game Settings

If you are not already using the built-in proxy, after configuring your upstream proxy configuration, update the in-game settings to ensure proper routing through the proxy server.

**Steps:**

1. **Enable Proxy Usage:** In your game's settings, set the **`useProxy:`** option is set to **`True`**.
2. **Set Proxy Connector Address:** Use the following address to connect to MITM Proxy (not your upstream proxy host):

   ```
   http://127.0.0.1:8080
   ```

**Important Notes:**

- The address `http://127.0.0.1:8080` routes through **MitMProxy (Man-in-the-Middle Proxy)**, which:
  - Modifies data to emulate a mobile device connection.
  - Adjusts headers as required by certain games (e.g., Blum).
- **Selenium**, the tool used for navigating Telegram Web pages, cannot directly authenticate proxies with usernames and passwords. MitMProxy handles this authentication seamlessly using your provided credentials.

---

## 4. Per-Session Proxy Connections

For users requiring **per-session proxy connections**, consider using **Docker containers**:

**Implementation:**

- **Create Separate Containers:** Set up individual Docker containers for each session requiring a distinct proxy connection.
- **Configure Proxies Individually:** Assign different proxy settings to each container as needed.

**Benefits:**

- **Isolation:** Each session runs independently, reducing cross-interference.
- **Flexibility:** Easily manage and scale multiple sessions with varied proxy configurations.

---

