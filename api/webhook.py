import os
import json
import logging

from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

logging.basicConfig(level=logging.INFO)

BOT_TOKEN = os.environ.get("7468327119:AAFzswUn3TAcDhI_OE62YP9AeEAl5JLm05w")

if not BOT_TOKEN:
    raise Exception("BOT_TOKEN missing in environment variables")

# ================= BOT =================
app = Application.builder().token(BOT_TOKEN).build()


# ================= COMMANDS =================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🚀 Bot running on Vercel")

async def ping(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🏓 Pong")


app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("ping", ping))


# initialize ONCE safely
import asyncio
asyncio.get_event_loop().run_until_complete(app.initialize())


# ================= VERCEL ENTRY =================
def handler(request):

    try:

        if request.method == "GET":
            return {
                "statusCode": 200,
                "body": "OK - Bot is alive"
            }

        body = request.body

        if isinstance(body, bytes):
            body = body.decode("utf-8")

        data = json.loads(body)

        update = Update.de_json(data, app.bot)

        # SAFE execution WITHOUT nested event loop conflicts
        import asyncio

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        loop.run_until_complete(app.process_update(update))

        return {
            "statusCode": 200,
            "body": "ok"
        }

    except Exception as e:
        logging.exception(e)

        return {
            "statusCode": 500,
            "body": str(e)
        }