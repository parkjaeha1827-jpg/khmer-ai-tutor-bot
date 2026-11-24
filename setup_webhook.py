import os
import sys
import socket
import httpx
from dotenv import load_dotenv

# Ensure fast IPv4 resolution on Windows
old_getaddrinfo = socket.getaddrinfo
def ipv4_getaddrinfo(*args, **kwargs):
    responses = old_getaddrinfo(*args, **kwargs)
    ipv4_responses = [r for r in responses if r[0] == socket.AF_INET]
    return ipv4_responses if ipv4_responses else responses
socket.getaddrinfo = ipv4_getaddrinfo

load_dotenv(override=True)

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()

if not TELEGRAM_BOT_TOKEN:
    print("❌ Error: TELEGRAM_BOT_TOKEN is not defined in your environment or .env file.")
    sys.exit(1)

TELEGRAM_API_BASE = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}"

def get_webhook_info():
    print("🔍 Fetching Telegram Webhook Information...")
    res = httpx.get(f"{TELEGRAM_API_BASE}/getWebhookInfo", timeout=15.0)
    data = res.json()
    if data.get("ok"):
        result = data["result"]
        print(f"📌 Webhook URL: {result.get('url') or '(None - webhook not set)'}")
        print(f"📌 Has Custom Certificate: {result.get('has_custom_certificate')}")
        print(f"📌 Pending Update Count: {result.get('pending_update_count', 0)}")
        print(f"📌 Max Connections: {result.get('max_connections')}")
        if result.get("last_error_date"):
            print(f"⚠️ Last Error Date: {result.get('last_error_date')}")
            print(f"⚠️ Last Error Message: {result.get('last_error_message')}")
        else:
            print("✅ Status: Clean (No webhook delivery errors reported)")
    else:
        print(f"❌ Failed to get webhook info: {data.get('description')}")

def set_webhook(url: str):
    # Ensure correct format
    url = url.rstrip("/")
    if not url.endswith("/api/webhook") and not url.endswith("/webhook"):
        webhook_url = f"{url}/api/webhook"
    else:
        webhook_url = url

    print(f"🚀 Registering Webhook with Telegram: {webhook_url}...")
    params = {
        "url": webhook_url,
        "allowed_updates": ["message", "edited_message"],
        "drop_pending_updates": True
    }
    res = httpx.post(f"{TELEGRAM_API_BASE}/setWebhook", json=params, timeout=20.0)
    data = res.json()
    if data.get("ok"):
        print(f"✅ Webhook successfully configured to: {webhook_url}")
        print(f"   Telegram Response: {data.get('description')}")
    else:
        print(f"❌ Failed to set webhook: {data.get('description')}")

def delete_webhook():
    print("🗑️ Deleting Webhook from Telegram...")
    res = httpx.post(
        f"{TELEGRAM_API_BASE}/deleteWebhook",
        json={"drop_pending_updates": True},
        timeout=15.0
    )
    data = res.json()
    if data.get("ok"):
        print("✅ Webhook removed successfully.")
    else:
        print(f"❌ Failed to remove webhook: {data.get('description')}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python setup_webhook.py info")
        print("  python setup_webhook.py set <VERCEL_DEPLOYMENT_URL>")
        print("  python setup_webhook.py delete")
        sys.exit(0)

    cmd = sys.argv[1].lower()
    if cmd == "info":
        get_webhook_info()
    elif cmd == "set":
        if len(sys.argv) < 3:
            print("❌ Error: Missing Vercel URL.")
            print("Example: python setup_webhook.py set https://khmer-ai-tutor-bot.vercel.app")
            sys.exit(1)
        set_webhook(sys.argv[2])
        print()
        get_webhook_info()
    elif cmd == "delete":
        delete_webhook()
    else:
        print(f"❌ Unknown command: {cmd}")
