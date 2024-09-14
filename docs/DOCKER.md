# Utilize Our Docker Image to Set Up the Telegram Claim Bot

Using Docker simplifies the setup of the Telegram Claim Bot by containerizing the application and its dependencies. This ensures a consistent environment across different architectures (x86/ARM64) and operating systems (Linux-based/Windows), eliminating issues related to dependency management and version conflicts. Docker also provides an easy way to deploy, scale, and manage the application, making it an ideal choice for running the Telegram Claim Bot efficiently.

To get started with Docker, you need to have Docker installed on your device.

## Installing Docker

### For Windows or Mac (Docker Desktop)

Download and install **Docker Desktop** from Docker's official website [here](https://www.docker.com/products/docker-desktop). 

**NOTE:** Docker Desktop provides the Docker Engine and needs to be running when you wish to use the Claim Bot, however individual command windows may be closed once the sessions are running as PM2 processes. 

- **Windows**:
  - Start the Docker Engine by opening Docker Desktop and leaving it open.
  - Open a Command Prompt (Press `Win + R`, type `cmd`, and press Enter).
  - Proceed to the [Common Commands](#common-commands) section below.

- **Mac**:
  - Start the Docker Engine by opening Docker Desktop and leaving it open.
  - Open a Terminal (Finder > Applications > Utilities > Terminal).
  - Proceed to the [Common Commands](#common-commands) section below.

### For Virtual Private Servers (CLI Access)

#### Amazon Linux

```bash
sudo yum update -y
sudo yum install docker -y
sudo service docker start
sudo usermod -aG docker $USER
exit
```

#### Ubuntu

```bash
sudo apt-get update -y
sudo apt-get install docker.io -y
sudo systemctl start docker
sudo systemctl enable docker
sudo usermod -aG docker $USER
exit
```

After running these commands, re-login to your VPS and proceed to the [Common Commands](#common-commands) section below.

## Common Commands

### Step 1: Create Your Container Based on Our Master Image (First Run Only)

To create and start the Docker container:

```bash
docker run -d --name telegram-claim-bot --restart unless-stopped thebrumby/telegram-claim-bot:latest
```

The Docker container inherits it's networking properties from the host computer. If you experience DNS issues using Docker's default network settings (e.g., GitHub fails to resolve and no games load), you can manually override the DNS using the commands below:

**Using Cloudflare's DNS (if the standard command above doesn't work)**

```bash
docker stop telegram-claim-bot
docker rm telegram-claim-bot
docker run -d --name telegram-claim-bot --dns="1.1.1.1" --restart unless-stopped thebrumby/telegram-claim-bot:latest
```

**Using Google's DNS (if the standard command above doesn't work)**

```bash
docker stop telegram-claim-bot
docker rm telegram-claim-bot
docker run -d --name telegram-claim-bot --dns="8.8.8.8" --restart unless-stopped thebrumby/telegram-claim-bot:latest
```

### Step 2: Operate Within the Container

To interact with the script, including adding accounts or monitoring:

```bash
docker exec -it telegram-claim-bot /bin/bash
```

### Step 3: Adding Games

Once inside the container, you can add games.

- To pick from a list of available scripts:

  ```bash
  ./launch.sh
  ```

- Or to specify the script by name:

  ```bash
  ./launch.sh hot
  ```

All other instructions are in line with the main `README.md`.

## Additional Docker Commands and Hints (used within the container)

  - To manually update to the latest code or add new games (the update script automatically does this every 12 hours)

  ```bash
  ./pull-games.sh
  ```

- To exit the container and return to the command prompt:

```bash
exit
```

## Additional Docker Commands and Hints (used at the command prompt outside the container)
- To start the container after a reboot or stopping:

  ```bash
  docker start telegram-claim-bot
  docker exec -it telegram-claim-bot /bin/bash
  ```

- To stop and remove the container:

  ```bash
  docker stop telegram-claim-bot
  docker rm telegram-claim-bot
  ```

---

All other instructions are in line with the main `README.md`.
