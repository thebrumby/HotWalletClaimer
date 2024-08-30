name: "Game suggestions"
description: "Recommend a game for inclusion in the Telegram Claim Bot"
title: "Game Suggestion: [Your Game Name Here]"
labels: ["suggestion", "game"]
body:
  - type: input
    id: bot_name
    attributes:
      label: "Bot Name"
      description: "Enter the name of the bot"
      placeholder: "Enter the bot's name"
    validations:
      required: true

  - type: input
    id: bot_handle
    attributes:
      label: "Bot Handle"
      description: "Enter the bot's Telegram handle, e.g., @HereWalletBot"
      placeholder: "@BotHandle"
    validations:
      required: true

  - type: textarea
    id: reason
    attributes:
      label: "Reason for Inclusion"
      description: "Why should this bot be included in the Telegram Claim Bot? Provide a brief explanation."
      placeholder: "Enter your reason here"
    validations:
      required: true
