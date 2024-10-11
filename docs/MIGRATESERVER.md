## Migrate Server

### On the server to be retired

1. Change directory into the `HotWalletBot` directory:
   ```bash
   cd HotWalletBot
   ```

2. Save the PM2 process list and create a `pm2-backup.json` from the dump:
   ```bash
   pm2 save
   cp ~/.pm2/dump.pm2 pm2-backup.json
   ```

3. Create a compressed tarball of necessary files:
   ```bash
   tar -czvf compressed_files.tar.gz selenium backups screenshots pm2-backup.json
   ```

### On the new server

4. Follow the general installation instructions at [LINUX.md](docs/LINUX.md).

5. Copy `compressed_files.tar.gz` into the `HotWalletBot` directory and decompress it:
   ```bash
   cp /path/to/compressed_files.tar.gz /path/to/HotWalletBot
   ```
   ```bash
   cd HotWalletBot
   tar -xzvf compressed_files.tar.gz
   ```

6. Create the recovery script:
   ```bash
   nano recover_pm2.sh
   ```

   Paste the following into `recover_pm2.sh`:
   ```
   #!/bin/bash

   # Path to your PM2 dump file
   DUMP_FILE="pm2-backup.json"

   # Base directory replacement
   OLD_BASE_DIR="/root/HotWalletBot"
   NEW_BASE_DIR="/home/ubuntu/HotWalletBot"

   # Iterate over each process in the dump file and start it with a delay
   jq -c '.[]' $DUMP_FILE | while read -r process; do
     NAME=$(echo $process | jq -r '.name')
     SCRIPT_PATH=$(echo $process | jq -r '.pm_exec_path' | sed "s|$OLD_BASE_DIR|$NEW_BASE_DIR|g")
     CWD=$(echo $process | jq -r '.pm_cwd' | sed "s|$OLD_BASE_DIR|$NEW_BASE_DIR|g")
     SESSION_NAME=$(echo $process | jq -r '.args[0] // empty')
     RELATIVE_SCRIPT_PATH=$(realpath --relative-to="$CWD" "$SCRIPT_PATH")
     ENV=$(echo $process | jq -c '.env')
     
     # Use the process name as session_name if not explicitly defined
     SESSION_NAME=${SESSION_NAME:-$NAME}
     
     # Check if the process is already running
     if pm2 describe "$NAME" >/dev/null 2>&1; then
       echo "Process $NAME is already running. Skipping..."
     else
       echo "Starting process: $NAME with script: $RELATIVE_SCRIPT_PATH in CWD: $CWD and session: $SESSION_NAME"
       # Change to the correct working directory before starting the process
       cd "$CWD" || exit
       NODE_NO_WARNINGS=1 pm2 start "$RELATIVE_SCRIPT_PATH" --name "$NAME" --interpreter "venv/bin/python3" --watch "$RELATIVE_SCRIPT_PATH" -- "$SESSION_NAME"
       
       echo "Waiting for 2 minutes before starting the next process..."
       sleep 120 # 120 seconds = 2 minutes
     fi
   done

   echo "All processes have been processed."
   ```

7. Make the script executable:
   ```bash
   chmod +x recover_pm2.sh
   ```

8. Execute the script:
   ```bash
   ./recover_pm2.sh
   ```

This process will migrate your PM2 processes, ensuring that scripts are started correctly on the new server with updated paths and settings.
