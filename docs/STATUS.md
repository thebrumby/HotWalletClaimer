# STATUS.md

## Overview

This script allows you to manage and monitor your PM2 processes for various games. You can view the status of all your accounts, delete processes, and see PM2 logs all in one place.

## Usage

To launch the status script, run:
```
./launch.sh status
```

## Options

### Sort by Time of Next Claim
To sort the processes by the time of the next claim:
```
t
```

### Delete Processes

#### Delete by Pattern
To delete all games matching a specific pattern:
```
delete [pattern]
```
**Example:**
```
delete HOT
```
This command will delete all processes that match the pattern "HOT".

#### Delete by Single ID
To delete a process by its ID:
```
delete [ID]
```
**Example:**
```
delete 51
```
This command will delete the process with ID 51.

#### Delete by Range of IDs
To delete a range of processes by their IDs:
```
delete [startID]-[endID]
```
**Example:**
```
delete 1-4
```
This command will delete all processes from ID 1 to ID 4.

#### Delete by Multiple IDs
To delete multiple processes by their IDs, separated by commas:
```
delete [ID1],[ID2],[ID3]
```
**Example:**
```
delete 1,3,5
```
This command will delete the processes with IDs 1, 3, and 5.

### View Status Logs

#### View Last 20 Balance and Status Logs
To view the last 20 balance and status logs for a specific process:
```
status [ID]
```
**Example:**
```
status 5
```
This command will show the last 20 balance and status logs for the process with ID 5.

### View PM2 Logs

#### View Last N Lines of PM2 Logs
To view the last N lines of raw PM2 logs for a specific process:
```
logs [ID] [lines]
```
**Example:**
```
logs 5 100
```
This command will show the last 100 lines of raw PM2 logs for the process with ID 5.

### Exit the Program
To exit the script:
```
exit
```
or simply press enter without typing any command.

## Examples

1. **Delete all games matching the pattern "Vertus":**
    ```
    delete Vertus
    ```

2. **Delete all saved Telegram accounts:**
    ```
    delete Telegram
    ```

3. **Delete processes in the range from 1 to 4:**
    ```
    delete 1-4
    ```

4. **Delete the process with ID 51:**
    ```
    delete 51
    ```

5. **Delete processes with IDs 1, 3, and 5:**
    ```
    delete 1,3,5
    ```

6. **Show the last 20 balance and status logs for process with ID 5:**
    ```
    status 5
    ```

7. **Show the last 100 raw lines from PM2 logs for process with ID 5:**
    ```
    logs 5 100
    ```
