# Utilize our Docker image to make a pre-built container
Using Docker simplifies the setup of the Telegram Claim Bot by containerizing the application and its dependencies. This ensures a consistent environment across different architectures (X86/ARM64) and operating systems (Linux-based/Windows), and eliminates issues related to dependency management and version conflicts. Docker also provides an easy way to deploy, scale, and manage the application, making it an ideal choice for running the Telegram Claim Bot efficiently.

To get started with Docker, you need to have Docker installed on your device. 

## Docker setup for Windows or Mac (Desktop Versions)

Download and install Docker Desktop from Docker's official website [here](https://www.docker.com/products/docker-desktop).

- **Windows**: Start the Docker Engine by opening Docker Desktop and leaving it open. Then, open a command prompt (Win key + 'R', type 'cmd' and hit Enter), and copy/paste the commands from the common section below.
- **Mac**: Start the Docker Engine by opening Docker Desktop and leaving it open. Then, open a terminal (Finder > Applications > Utilities > Terminal), and copy/paste the commands from the common section below.

## Docker setup for Virtual Private Servers (CLI access)
<table>
  <tr>
    <th>Docker Step 1 (Amazon Linux)</th>
    <th>Docker Step 1 (Ubuntu)</th>
  </tr>
  <tr>
    <td>
      <pre>
sudo yum update -y
sudo yum install docker -y
sudo service docker start
sudo usermod -aG docker $USER
exit
      </pre>
    </td>
    <td>
      <pre>
sudo apt-get update -y
sudo apt-get install docker.io -y
sudo systemctl start docker
sudo systemctl enable docker
sudo usermod -aG docker $USER
exit
      </pre>
    </td>
  </tr>
  <tr>
    <td colspan="2">
      Step 2 - Open the Terminal again and start the Claim Bot
    </td>
  </tr>
</table>

## The following commands are common to all operating systems.

Create your container based on our master image (first run only):
```
docker run -d --name telegram-claim-bot --restart unless-stopped thebrumby/telegram-claim-bot:latest
```

To operate within the container to interact with the script, including adding accounts or monitoring:
```
docker exec -it telegram-claim-bot /bin/bash
```

To exit the container and return to the command promt:
```
exit
```

To start the session after a reboot or stopping:
```
docker start telegram-claim-bot
docker exec -it telegram-claim-bot /bin/bash
```

To remove the container:
```
docker stop telegram-claim-bot
docker rm telegram-claim-bot
```

To update for the latest code or new games:
```
./pull-games.sh
```

To add a game:

- To pick from a list of available scripts:
```
./launch.sh
```

- Or to specify the script by name:
```
./launch.sh hot
```

All other instructions are in line with the main README.md.
