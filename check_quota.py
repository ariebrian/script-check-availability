import requests
import os
import json
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

API_URL = os.getenv("API_URL", "YOUR_API_URL_HERE")
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN", "YOUR_TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "YOUR_TELEGRAM_CHAT_ID")

def send_telegram_message(message):
    """Sends a message to the specified Telegram chat."""
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message,
        "parse_mode": "HTML"
    }
    try:
        response = requests.post(url, json=payload)
        response.raise_for_status()
        print(f"[{datetime.now()}] Telegram alert sent successfully.")
    except Exception as e:
        print(f"[{datetime.now()}] Error sending Telegram message: {e}")

def check_quota():
    """Hits the API and checks for available quota."""
    print(f"[{datetime.now()}] Checking quota...")
    try:
        response = requests.get(API_URL, timeout=10)
        response.raise_for_status()
        data = response.json()

        if not data.get("status"):
            print(f"[{datetime.now()}] API Error: {data.get('message')}")
            return

        available_sessions = []
        # Traverse the JSON structure
        sessions = data.get("data", {}).get("session", [])
        for session in sessions:
            session_label = session.get("label")
            details = session.get("session_detail", [])
            
            for detail in details:
                quota = detail.get("available_quota", 0)
                if quota > 0:
                    member_name = detail.get("jkt48_member_name", "Unknown Member")
                    available_sessions.append(f"<b>{member_name}</b> - {session_label} (Quota: {quota})")

        if available_sessions:
            message = "🚨 <b>Quota Available!</b> 🚨\n\n" + "\n".join(available_sessions)
            send_telegram_message(message)
        else:
            print(f"[{datetime.now()}] No available quota found.")

    except Exception as e:
        print(f"[{datetime.now()}] Error during check: {e}")

def main():
    print(f"[{datetime.now()}] Starting single check...")
    check_quota()

if __name__ == "__main__":
    main()
