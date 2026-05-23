import os
import json
import urllib.request
from flask import Flask, request, jsonify

app = Flask(__name__)

BOT_TOKEN = os.getenv("BOT_TOKEN", "YOUR_BOT_TOKEN")
API_URL = f"https://api.telegram.org/bot{BOT_TOKEN}"


# -------------------------
# SEND MESSAGE
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
# TELEGRAM HANDLER
# -------------------------
def handle_update(update):
    message = update.get("message")

    if not message:
        return

    chat_id = message.get("chat", {}).get("id")
    text = message.get("text", "")

    if not chat_id:
        return

    if text == "/start":
        send_message(chat_id, "⚡ Flask bot running on Vercel")

    elif text == "/ping":
        send_message(chat_id, "pong ⚡")

    else:
        send_message(chat_id, f"Echo: {text}")


# -------------------------
# HEALTH CHECK
# -------------------------
@app.route("/", methods=["GET"])
def home():
    return jsonify({"status": "alive"})


# -------------------------
# TELEGRAM WEBHOOK
# -------------------------
@app.route("/webhook", methods=["POST"])
def webhook():
    try:
        update = request.get_json()
        handle_update(update)
        return jsonify({"ok": True})

    except Exception as e:
        print("webhook error:", e)
        return jsonify({"ok": False})


# REQUIRED FOR VERCEL
app = app