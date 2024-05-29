module.exports = {
    apps: [
      {
        name: "daily-update",
        script: "./update.sh",
        interpreter: "/bin/bash",
        watch: false,
        env: {
          NODE_ENV: "production"
        }
      }
    ]
  };