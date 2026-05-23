import json
import urllib.request
import urllib.error
import os


BOT_TOKEN = os.getenv("BOT_TOKEN", "YOUR_BOT_TOKEN")
API_URL = f"https://api.telegram.org/bot{BOT_TOKEN}"


# -------------------------
# SEND MESSAGE (SAFE)
# -------------------------
def send_message(chat_id, text):
    try:
        payload = json.dumps({
            "chat_id": chat_id,
            "text": text
        }).encode("utf-8")

        req = urllib.request.Request(
            f"{API_URL}/sendMessage",
            data=payload,
            headers={"Content-Type": "application/json"}
        )

        urllib.request.urlopen(req, timeout=3)

    except Exception as e:
        print("send_message error:", e)


# -------------------------
# BOT LOGIC
# -------------------------
def handle_update(update):
    try:
        message = update.get("message")
        if not message:
            return

        chat_id = message.get("chat", {}).get("id")
        text = message.get("text", "")

        if not chat_id:
            return

        if text == "/start":
            send_message(chat_id, "⚡ Bot is running on Vercel")

        elif text == "/ping":
            send_message(chat_id, "pong ⚡")

        else:
            send_message(chat_id, f"Echo: {text}")

    except Exception as e:
        print("handle_update error:", e)


# -------------------------
# VERCEL SERVERLESS HANDLER
# -------------------------
def handler(request):
    try:
        method = request.get("method", "")

        # GET request (health check)
        if method == "GET":
            return {
                "statusCode": 200,
                "body": json.dumps({"status": "alive"})
            }

        # POST request (Telegram webhook)
        if method == "POST":
            try:
                body = request.get("body", "{}")
                update = json.loads(body)

                handle_update(update)

                return {
                    "statusCode": 200,
                    "body": json.dumps({"ok": True})
                }

            except Exception as e:
                print("POST error:", e)

                return {
                    "statusCode": 200,
                    "body": json.dumps({"ok": False})
                }

        return {
            "statusCode": 200,
            "body": json.dumps({"ok": False, "msg": "invalid method"})
        }

    except Exception as e:
        print("FATAL ERROR:", e)

        return {
            "statusCode": 200,
            "body": json.dumps({"ok": False})
        }