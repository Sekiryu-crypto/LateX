import json
from http.server import BaseHTTPRequestHandler
import urllib.request
import urllib.error
import os


BOT_TOKEN = os.getenv("BOT_TOKEN", "YOUR_BOT_TOKEN")
API_URL = f"https://api.telegram.org/bot{BOT_TOKEN}"


# -------------------------
# SAFE SEND MESSAGE (NON-BLOCKING STYLE)
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

        # IMPORTANT: short timeout for Vercel stability
        urllib.request.urlopen(req, timeout=3)

    except urllib.error.URLError as e:
        print("Telegram API error:", e)
    except Exception as e:
        print("send_message error:", e)


# -------------------------
# BOT LOGIC
# -------------------------
def handle_update(update):
    try:
        message = update.get("message", {})
        if not message:
            return

        chat_id = message.get("chat", {}).get("id")
        text = message.get("text", "")

        if not chat_id:
            return

        if text == "/start":
            send_message(chat_id, "⚡ Bot is alive on Vercel")

        elif text == "/ping":
            send_message(chat_id, "pong ⚡")

        else:
            send_message(chat_id, f"Echo: {text}")

    except Exception as e:
        print("handle_update error:", e)


# -------------------------
# VERCEL HANDLER
# -------------------------
class handler(BaseHTTPRequestHandler):

    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-type", "application/json")
        self.end_headers()
        self.wfile.write(b'{"status":"alive"}')

    def do_POST(self):
        try:
            content_length = self.headers.get("Content-Length")

            if not content_length:
                self.send_response(200)
                self.end_headers()
                self.wfile.write(b'{"ok":false,"error":"no content"}')
                return

            body = self.rfile.read(int(content_length))
            update = json.loads(body.decode("utf-8"))

            handle_update(update)

            self.send_response(200)
            self.send_header("Content-type", "application/json")
            self.end_headers()
            self.wfile.write(b'{"ok":true}')

        except Exception as e:
            print("WEBHOOK ERROR:", e)

            # ALWAYS return 200 so Telegram doesn't retry spam
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b'{"ok":false}')