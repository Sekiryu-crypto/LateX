import os
import json
import logging
from http.server import BaseHTTPRequestHandler

from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

import asyncio

# ================= LOGGING =================
logging.basicConfig(level=logging.INFO)

# ================= BOT TOKEN =================
BOT_TOKEN = os.environ.get("7468327119:AAFzswUn3TAcDhI_OE62YP9AeEAl5JLm05w")

if not BOT_TOKEN:
    raise Exception("BOT_TOKEN is missing in Vercel env variables")

# ================= APP =================
app = Application.builder().token(BOT_TOKEN).build()

# ================= COMMANDS =================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Bot is running 🚀")

async def ping(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Pong 🏓")

app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("ping", ping))


# ================= INIT ONCE (SAFE) =================
asyncio.get_event_loop().run_until_complete(app.initialize())


# ================= HANDLER =================
class handler(BaseHTTPRequestHandler):

    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"OK - Bot is live")

    def do_POST(self):
        try:
            length = int(self.headers.get("content-length", 0))
            body = self.rfile.read(length)

            update_data = json.loads(body.decode("utf-8"))
            update = Update.de_json(update_data, app.bot)

            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

            loop.run_until_complete(app.process_update(update))

            self.send_response(200)
            self.end_headers()
            self.wfile.write(b"ok")

        except Exception as e:
            logging.exception(e)

            self.send_response(500)
            self.end_headers()
            self.wfile.write(str(e).encode())