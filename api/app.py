import json
from http.server import BaseHTTPRequestHandler
import urllib.request

BOT_TOKEN = "YOUR_BOT_TOKEN"
API_URL = f"https://api.telegram.org/bot{BOT_TOKEN}"


# -------------------------
# SEND MESSAGE FUNCTION
# -------------------------
def send_message(chat_id, text):
    try:
        data = json.dumps({
            "chat_id": chat_id,
            "text": text
        }).encode("utf-8")

        req = urllib.request.Request(
            f"{API_URL}/sendMessage",
            data=data,
            headers={"Content-Type": "application/json"}
        )

        urllib.request.urlopen(req, timeout=2)

    except Exception as e:
        print("send error:", e)


# -------------------------
# BOT LOGIC
# -------------------------
def handle_update(update):
    message = update.get("message")

    if not message:
        return

    chat_id = message["chat"]["id"]
    text = message.get("text", "")

    if text == "/start":
        send_message(chat_id, "⚡ Bot is working on Vercel")

    elif text == "/ping":
        send_message(chat_id, "pong ⚡")

    else:
        send_message(chat_id, f"Echo: {text}")


# -------------------------
# VERCEL HANDLER
# -------------------------
class handler(BaseHTTPRequestHandler):

    # FIX 501 ERROR (browser / GET request)
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-type", "application/json")
        self.end_headers()
        self.wfile.write(b'{"status":"alive"}')

    # TELEGRAM WEBHOOK (POST)
    def do_POST(self):
        try:
            content_length = int(self.headers["Content-Length"])
            body = self.rfile.read(content_length)
            update = json.loads(body.decode("utf-8"))

            handle_update(update)

            self.send_response(200)
            self.send_header("Content-type", "application/json")
            self.end_headers()
            self.wfile.write(b'{"ok":true}')

        except Exception as e:
            print("error:", e)

            self.send_response(200)
            self.end_headers()
            self.wfile.write(b'{"ok":false}')