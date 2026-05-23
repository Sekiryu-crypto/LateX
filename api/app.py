import json
import asyncio
import httpx
from http.server import BaseHTTPRequestHandler

BOT_TOKEN = "YOUR_BOT_TOKEN"
API_URL = f"https://api.telegram.org/bot{BOT_TOKEN}"

client = httpx.AsyncClient(timeout=5)


# ---------------------------
# FAST MESSAGE SENDER
# ---------------------------
async def send_message(chat_id, text):
    try:
        await client.post(
            f"{API_URL}/sendMessage",
            json={
                "chat_id": chat_id,
                "text": text
            }
        )
    except Exception as e:
        print("send error:", e)


# ---------------------------
# CORE LOGIC
# ---------------------------
async def handle_update(update):
    try:
        message = update.get("message")

        if not message:
            return

        chat_id = message["chat"]["id"]
        text = message.get("text", "")

        # COMMANDS
        if text == "/start":
            await send_message(chat_id, "⚡ Bot is live on Vercel (fast mode)")

        elif text == "/ping":
            await send_message(chat_id, "pong ⚡")

        else:
            await send_message(chat_id, f"Echo: {text}")

    except Exception as e:
        print("handler error:", e)


# ---------------------------
# VERCEL ENTRY POINT
# ---------------------------
class handler(BaseHTTPRequestHandler):
    def do_POST(self):
        try:
            content_length = int(self.headers["Content-Length"])
            body = self.rfile.read(content_length)
            update = json.loads(body.decode("utf-8"))

            # ⚡ IMPORTANT: DO NOT BLOCK RESPONSE
            asyncio.run(handle_update(update))

            self.send_response(200)
            self.send_header("Content-type", "application/json")
            self.end_headers()
            self.wfile.write(b'{"ok":true}')

        except Exception as e:
            print("webhook error:", e)

            self.send_response(200)
            self.end_headers()
            self.wfile.write(b'{"ok":false}')