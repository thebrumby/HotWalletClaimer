import os
import json

# Define sessions and settings files
status_file_path = "status.txt"
settings_file = "variables.txt"
settings = {}

def output(string, level):
    if settings['verboseLevel'] >= level:
        print(string)

def load_settings():
    global settings, settings_file
    default_settings = {
        "forceClaim": False,
        "debugIsOn": False,
        "hideSensitiveInput": True,
        "screenshotQRCode": True,
        "maxSessions": 1,
        "verboseLevel": 2,
        "lowestClaimOffset": 0,
        "highestClaimOffset": 15,
        "forceNewSession": False,
        "useProxy": False,
        "proxyAddress": "http://127.0.0.1:8080"
    }

    if os.path.exists(settings_file):
        with open(settings_file, "r") as f:
            loaded_settings = json.load(f)
        # Filter out unused settings from previous versions
        settings = {k: loaded_settings.get(k, v) for k, v in default_settings.items()}
        output("Settings loaded successfully.", 3)
    else:
        settings = default_settings
        save_settings()

def save_settings():
    global settings, settings_file
    with open(settings_file, "w") as f:
        json.dump(settings, f)
    output("Settings saved successfully.", 3)

def update_settings():
    global settings

    def update_setting(setting_key, message, default_value):
        current_value = settings.get(setting_key, default_value)
        response = input(f"\n{message} (Y/N, press Enter to keep current [{current_value}]): ").strip().lower()
        if response == "y":
            settings[setting_key] = True
        elif response == "n":
            settings[setting_key] = False

    update_setting("forceClaim", "Shall we force a claim on first run? Does not wait for the timer to be filled", settings["forceClaim"])
    update_setting("debugIsOn", "Should we enable debugging? This will save screenshots in your local drive", settings["debugIsOn"])
    update_setting("hideSensitiveInput", "Should we hide sensitive input? Your phone number and seed phrase will not be visible on the screen", settings["hideSensitiveInput"])
    update_setting("screenshotQRCode", "Shall we allow log in by QR code? The alternative is by phone number and one-time password", settings["screenshotQRCode"])

    try:
        new_max_sessions = int(input(f"\nEnter the number of max concurrent claim sessions. Additional claims will queue until a session slot is free.\n(current: {settings['maxSessions']}): "))
        settings["maxSessions"] = new_max_sessions
    except ValueError:
        output("Number of sessions remains unchanged.", 1)

    try:
        new_verbose_level = int(input("\nEnter the number for how much information you want displaying in the console.\n 3 = all messages, 2 = claim steps, 1 = minimal steps\n(current: {}): ".format(settings['verboseLevel'])))
        if 1 <= new_verbose_level <= 3:
            settings["verboseLevel"] = new_verbose_level
            output("Verbose level updated successfully.", 2)
        else:
            output("Verbose level remains unchanged.", 2)
    except ValueError:
        output("Verbose level remains unchanged.", 2)

    try:
        new_lowest_offset = int(input("\nEnter the lowest possible offset for the claim timer (valid values are -30 to +30 minutes)\n(current: {}): ".format(settings['lowestClaimOffset'])))
        if -30 <= new_lowest_offset <= 30:
            settings["lowestClaimOffset"] = new_lowest_offset
            output("Lowest claim offset updated successfully.", 2)
        else:
            output("Invalid range for lowest claim offset. Please enter a value between -30 and +30.", 2)
    except ValueError:
        output("Lowest claim offset remains unchanged.", 2)

    try:
        new_highest_offset = int(input("\nEnter the highest possible offset for the claim timer (valid values are 0 to 60 minutes)\n(current: {}): ".format(settings['highestClaimOffset'])))
        if 0 <= new_highest_offset <= 60:
            settings["highestClaimOffset"] = new_highest_offset
            output("Highest claim offset updated successfully.", 2)
        else:
            output("Invalid range for highest claim offset. Please enter a value between 0 and 60.", 2)
    except ValueError:
        output("Highest claim offset remains unchanged.", 2)

    if settings["lowestClaimOffset"] > settings["highestClaimOffset"]:
        settings["lowestClaimOffset"] = settings["highestClaimOffset"]
        output("Adjusted lowest claim offset to match the highest as it was greater.", 2)

    update_setting("useProxy", "Use Proxy?", settings["useProxy"])

    if settings["useProxy"]:
        proxy_address = input(f"\nEnter the Proxy IP address and port (current: {settings['proxyAddress']}): ").strip()
        if proxy_address:
            settings["proxyAddress"] = proxy_address

    save_settings()

    update_setting("forceNewSession", "Overwrite existing session and Force New Login? Use this if your saved session has crashed\nOne-Time only (setting not saved): ", settings["forceNewSession"])

    output("\nRevised settings:", 1)
    for key, value in settings.items():
        output(f"{key}: {value}", 1)
    output("", 1)
