from telethon import TelegramClient
from telethon.tl.functions.channels import JoinChannelRequest
import re
import requests
import time
import argparse

# URL to fetch the channel list (replace with your actual URL)
table_url = "https://raw.githubusercontent.com/fastfire/deepdarkCTI/refs/heads/main/telegram_threat_actors.md"

# File to store successfully subscribed channel URLs
success_log_file = "subscribed_channels.txt"
error_log_file = "known_error_log.txt"

def fetch_and_parse_table(url):
    """
    Fetch the channel table and extract valid channels.
    """
    try:
        response = requests.get(url)
        response.raise_for_status()
        raw_table = response.text
        rows = raw_table.strip().split("\n")[2:]
        channels = []

        for row in rows:
            columns = row.split("|")[1:-1]
            while len(columns) < 4:
                columns.append("")

            channels.append(
                {
                    "url": columns[0].strip(),
                    "status": columns[1].strip(),
                    "name": columns[2].strip(),
                    "type": columns[3].strip(),
                }
            )
        return channels
    except Exception as e:
        print(f"Failed to fetch or parse the table: {e}")
        return []

def load_known_error_channels():
    """
    Load the list of already known error channels.
    """
    try:
        with open(error_log_file, "r") as file:
            return set(line.strip() for line in file)
    except FileNotFoundError:
        return set()

def save_known_error_channel(channel_url):
    """
    Save a known error channel to the log file.
    """
    with open(error_log_file, "a") as file:
        file.write(channel_url + "\n")

def load_subscribed_channels():
    """
    Load the list of already subscribed channels to prevent duplicates.
    """
    try:
        with open(success_log_file, "r") as file:
            return set(line.strip() for line in file)
    except FileNotFoundError:
        return set()

def save_subscribed_channel(channel_url):
    """
    Save a successfully subscribed channel to the log file.
    """
    with open(success_log_file, "a") as file:
        file.write(channel_url + "\n")

def subscribe_to_channels(client, valid_channels):
    """
    Subscribe to channels sequentially with retry handling.
    """
    subscribed_channels = load_subscribed_channels()
    known_error_channels = load_known_error_channels()
    max_retries = 8

    for channel_url in valid_channels:
        # Check if already subscribed
        if channel_url in subscribed_channels or channel_url in known_error_channels:
            continue

        # Extract the username or invite link
        match = re.search(r"t\.me(?:/.+)?/(\S+)", channel_url)
        if not match:
            print(f"Invalid URL format: {channel_url}")
            continue

        username_or_invite = match.group(1)
        retries = 0
        sleep_timer = 128

        while retries < max_retries:
            try:
                # Join the channel
                #client(JoinChannelRequest(username_or_invite)) # This does not work - call must be async
                client.loop.run_until_complete(client(JoinChannelRequest(username_or_invite)))
                print(f"Successfully subscribed to {channel_url}")

                # Log the successful subscription
                save_subscribed_channel(channel_url)
                break

            except Exception as e:
                retries += 1
                print(
                    f"Error joining {channel_url} (Attempt {retries}/{max_retries}): {e}"
                )

                # Handle wait time errors
                wait_match = re.search(r"A wait of (\d+) seconds", str(e))
                if wait_match:
                    # Exponential backoff
                    sleep_timer = min(sleep_timer * 2, 3600)
                    print(f"Retrying in {sleep_timer} seconds...")
                    time.sleep(sleep_timer)
                else:
                    save_known_error_channel(channel_url)
                    break

        # Prevent rapid requests even if successful
        time.sleep(5)  # 5-second delay before the next channel

def main():
    parser = argparse.ArgumentParser(description="A script to interact with Telegram using Telethon.")
    parser.add_argument("--api_id", required=True, type=int, help="Your Telegram API ID (numeric).")
    parser.add_argument("--api_hash", required=True, type=str, help="Your Telegram API Hash (32-character hexadecimal string).")
    parser.add_argument("--phone", required=True, type=str, help="Your phone number in international format (e.g., +1234567890).")
    
    # Parse the arguments
    args = parser.parse_args()
    
    # Validate the inputs (optional)
    if not re.match(r"^[0-9a-fA-F]{32}$", args.api_hash):
        raise ValueError("API Hash must be a 32-character hexadecimal string.")
    if not re.match(r"^\+\d{10,15}$", args.phone):
        raise ValueError("Phone number must be in international format, e.g., +1234567890.")
    
    print("\n--- Starting Telegram Subscription Program ---\n")

    print("1. Fetching and parsing the channel table...")
    channels = fetch_and_parse_table(table_url)
    print(f"   - Total channels found: {len(channels)}")

    # Filter valid channels
    valid_channels = [
        channel["url"]
        for channel in channels
        if channel["status"] in ["VALID", "ONLINE"]
    ]

    # Exit if no valid channels found
    if not valid_channels:
        print("   - No valid channels found. Exiting...")
        return

    print(f"   - Valid channels to subscribe to: {len(valid_channels)}")
    print(f"   - Skipping already subscribed channels...")

    print("\n2. Initializing the Telegram client...")
    client = TelegramClient("session_name", args.api_id, args.api_hash)

    try:
        print("   - Starting Telegram client...")
        client.start(phone=args.phone)
        print("   - Client successfully started.")

        print("\n3. Subscribing to channels...")
        subscribe_to_channels(client, valid_channels)

    except Exception as e:
        print(f"   - Error during execution: {e}")

    finally:
        print("\n4. Disconnecting the client...")
        client.disconnect()
        print("   - Client successfully disconnected.")

    print("\n--- Program completed successfully ---\n")

if __name__ == "__main__":
    main()

