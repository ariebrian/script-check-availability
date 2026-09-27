import requests
import os
import json
import time
from datetime import datetime
from dotenv import load_dotenv
from playwright.sync_api import sync_playwright

# Load environment variables
load_dotenv()

API_URL = os.getenv("API_URL", "https://jkt48.com/api/v1/exclusives/EX5B99/bonus?lang=id")
CHECK_INTERVAL_SECONDS = int(os.getenv("CHECK_INTERVAL_SECONDS", "60"))
STATE_FILE = os.getenv("STATE_FILE", "quota_state.json")
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

# API_URL is protected by Cloudflare's bot-challenge, which blocks plain HTTP
# clients (requests/cloudscraper). A real headless browser passes it, so we
# fetch through Playwright instead of a raw HTTP request.
BROWSER_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)


def load_previous_quotas():
    """Loads the last known quota per session_detail_code from disk."""
    try:
        with open(STATE_FILE, "r") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def save_previous_quotas(previous_quotas):
    """Persists the last known quota per session_detail_code to disk."""
    with open(STATE_FILE, "w") as f:
        json.dump(previous_quotas, f)

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

def check_quota(page, previous_quotas):
    """Loads the API through a real browser (to pass Cloudflare) and alerts only on session_detail_codes whose quota increased."""
    print(f"[{datetime.now()}] Checking quota...")
    try:
        response = page.goto(API_URL, wait_until="networkidle", timeout=30000)
        if response is None or response.status != 200:
            status = response.status if response else "no response"
            print(f"[{datetime.now()}] Unexpected HTTP status: {status}")
            return
        data = response.json()

        if not data.get("status"):
            print(f"[{datetime.now()}] API Error: {data.get('message')}")
            return

        increased_sessions = []
        # Traverse the JSON structure
        sessions = data.get("data", [])
        # sessions[0]["session_members"][0]["available_quota"] = 1
        # print(sessions[0].get("session_members")[0].get("available_quota"))
        for session in sessions:
            session_label = session.get("label")
            session_date = session.get("date")
            start_time = session.get("start_time")
            end_time = session.get("end_time")
            members = session.get("session_members", [])

            for member in members:
                session_detail_code = member.get("session_detail_code", "")
                quota = member.get("available_quota", 0)
                previous_quota = previous_quotas.get(session_detail_code, 0)

                if quota > previous_quota:
                    member_name = member.get("member_name", "Unknown Member")
                    jalur_label = member.get("label", "")
                    increased_sessions.append(
                        f"<b>{member_name}</b> - {jalur_label} - {session_label} "
                        f"({session_date} {start_time}-{end_time}) "
                        f"(Quota: {previous_quota} -> {quota})\n"
                        f"Code: {session_detail_code}"
                    )

                previous_quotas[session_detail_code] = quota

        save_previous_quotas(previous_quotas)

        if increased_sessions:
            message = "🚨 <b>TESTING TESTING Quota Bertambah!</b> 🚨\n\n" + "\n".join(increased_sessions)
            # print(message)
            send_telegram_message(message)
        else:
            print(f"[{datetime.now()}] No quota increase found.")

    except Exception as e:
        print(f"[{datetime.now()}] Error during check: {e}")

def main():
    print(f"[{datetime.now()}] Starting quota checker job (interval: {CHECK_INTERVAL_SECONDS}s)...")
    previous_quotas = load_previous_quotas()

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(user_agent=BROWSER_USER_AGENT)
        try:
            while True:
                start = time.monotonic()
                check_quota(page, previous_quotas)
                elapsed = time.monotonic() - start
                time.sleep(max(0, CHECK_INTERVAL_SECONDS - elapsed))
        finally:
            browser.close()

if __name__ == "__main__":
    main()
