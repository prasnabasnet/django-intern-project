import os
import requests

def send_discord_alert(message):
    bot_token = os.getenv("BOT_TOKEN")
    channel_id = os.getenv("BOT_CHAT_ID")


    if not bot_token or not channel_id:
        return
    
    url = f"https://discord.com/api/v10/channels/{channel_id}/messages"
    headers = {
        "Authorization": f"Bot {bot_token}",
        "Content-Type": "application/json",
    }
    payload = {"content": message}

    try:
        response = requests.post(url, json=payload, headers=headers, timeout=5)
        response.raise_for_status()

    except Exception as e:
        print(f"Failed to send Discord alert: {str(e)}")