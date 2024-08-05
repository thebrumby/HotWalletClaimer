# Manage disk space by configuring PM2 logs.

If you have limited hard disk space on the machine you are running the scripts on, you need to adjust the number of games you initiate to fit within the constraints of your hardware. Each game session uses between 100 and 400 MB of disk space, depending on which game you are running. Most of the space is consumed by the browser cache file, which stores a copy of the game assets on your machine to avoid reloading them every time. Additionally, PM2 will store logs on the progress of your claims, so you may need to use a method similar to the one below to curate or manage your logs.

We have no knowledge or control over the size of your hardware or the number of scripts that you will install. It is up to each user to monitor their hardware resources and ensure they are capable of running the number of scripts you initiate.

If hard drive space is a limiting factor, you can instruct PM2 on how to rotate the logs. In this example, each process is allowed to maintain up to 10 x 1 MB logs, although the majority will be compressed. This is the maximum log size for EVERY process shown when you type `pm2 list`.

Example:
```
pm2 set pm2-logrotate:max_size 1M
pm2 set pm2-logrotate:retain 10
pm2 set pm2-logrotate:compress true
pm2 set pm2-logrotate:dateFormat 'YYYY-MM-DD_HH-mm-ss'
pm2 set pm2-logrotate:workerInterval 30
pm2 set pm2-logrotate:rotateInterval '0 0 0 * * * * *' # Rotate daily
```

### Here's what each PM2 Logrotate configuration command means:

- `pm2 set pm2-logrotate:max_size 1M`

  Sets the maximum log file size to 1 megabyte. When a log file reaches this size, it will be rotated.

- `pm2 set pm2-logrotate:retain 10`

  Retains the last 10 rotated log files and deletes older ones to save disk space.

- `pm2 set pm2-logrotate:compress true`

  Enables compression for rotated log files, saving disk space.

- `pm2 set pm2-logrotate:dateFormat 'YYYY-MM-DD_HH-mm-ss'`

  Sets the timestamp format for log file names to year-month-day_hour-minute-second.

- `pm2 set pm2-logrotate:workerInterval 30`

  The log rotation worker checks every 30 seconds if any log file needs rotation based on size.

- `pm2 set pm2-logrotate:rotateInterval '0 0 0 * * * * *'`

  Schedules log rotation to occur daily at midnight.

### To delete pm2-logrotate without terminating sessions, follow these steps:

1. Disable pm2-logrotate:
   ```
   pm2 set pm2-logrotate:enable false
   ```

2. Uninstall pm2-logrotate:
   ```
   pm2 uninstall pm2-logrotate
   ```

This will remove the pm2-logrotate module without affecting your running PM2 processes.
